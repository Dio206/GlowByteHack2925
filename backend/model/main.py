import random
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from catboost import CatBoostClassifier
from sklearn.metrics import classification_report, roc_auc_score
from fastapi.middleware.cors import CORSMiddleware
import os
import io
from datetime import datetime
from typing import List, Dict, Any

script_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(script_dir, "catboost_model.cbm")

PREDICTIONS_CACHE = {} 

# =========================================================================================
# Вспомогательные функции
# =========================================================================================

def format_card_data(row: pd.Series) -> Dict[str, Any]:
    probability = row['probability']
    status = "В зоне высокого риска" if probability > 0.60 else "Норма"
    
    return {
        "Номер штабеля": int(row['stack_id']),
        "Дата риска": row['date'].strftime('%Y-%m-%d'),
        "Статус": status,
        "Возраст угля (дней)": int(row['coal_age_days']),
        "Тип угля": row['coal_type'],
        "Вероятность риска (%)": f"{probability * 100:.2f}%",
        "Вероятность риска (RAW)": float(probability), 
        "Скорость нагрева (RoR, °C/день)": f"{row['temp_ror']:.2f}",
        "Макс. температура (°C)": f"{row['temp_measured']:.2f}",
        "Координата X": float(row['coord_x']), 
        "Координата Y": float(row['coord_y']) 
    }

def load_data_from_files(df_weather_raw, df_supplies_raw, df_temp_raw):
    """
    Препроцессинг, динамическая генерация координат и инженерия признаков.
    """
    df_supplies_raw['Start_Date'] = pd.to_datetime(df_supplies_raw['ВыгрузкаНаСклад']).dt.normalize()
    df_supplies_raw['End_Date'] = pd.to_datetime(df_supplies_raw['ПогрузкаНаСудно']).dt.normalize()
    
    stack_coords = {}
    
    LAT_MIN, LAT_MAX = 44.7, 44.8 
    LON_MIN, LON_MAX = 37.7, 37.8 
    
    for stack_id in df_supplies_raw['Штабель'].unique():
        random.seed(int(stack_id) * 12345) 
        stack_coords[stack_id] = {
            'stack_id': stack_id,
            'coord_x': random.uniform(LAT_MIN, LAT_MAX), 
            'coord_y': random.uniform(LON_MIN, LON_MAX)  
        }
    df_coords = pd.DataFrame(list(stack_coords.values())) 
    
    stack_daily_rows = []
    for _, row in df_supplies_raw.iterrows():
        end_date = row['End_Date'] if pd.notnull(row['End_Date']) else pd.to_datetime("2021-12-31")
        start_date = row['Start_Date']
        stack_id = row['Штабель']
        
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        for date in date_range:
            stack_daily_rows.append({
                'stack_id': stack_id,
                'date': date.normalize(),
                'coal_type': row.get('Наим. ЕТСНГ', 'Unknown'),
                'initial_amount': row.get('На склад, тн', 0),
                'coal_age_days': (date.normalize() - start_date).days 
            })
            
    df_master = pd.DataFrame(stack_daily_rows)
    
    df_master = df_master.drop_duplicates(subset=['stack_id', 'date'], keep='first')
    
    df_master = pd.merge(df_master, df_coords, on='stack_id', how='left')

    df_weather_raw['date'] = pd.to_datetime(df_weather_raw['date']).dt.normalize()
    df_weather_raw = df_weather_raw.groupby('date').agg({
        't': 'mean', 'wind_dir': 'mean', 'v_avg': 'mean', 'humidity': 'mean'
    }).reset_index()
    df_master = df_master.merge(df_weather_raw, on='date', how='left')

    df_temp_raw['date'] = pd.to_datetime(df_temp_raw['Дата акта']).dt.normalize()
    df_temp_raw = df_temp_raw.rename(columns={'Штабель': 'stack_id', 'Максимальная температура': 'temp_measured'})
    df_temp_raw = df_temp_raw[['stack_id', 'date', 'temp_measured']].drop_duplicates(subset=['stack_id', 'date'], keep='first')
    
    df_master = df_master.merge(df_temp_raw, on=['stack_id', 'date'], how='left')
    
    df_master['temp_measured'] = df_master.groupby('stack_id')['temp_measured'].ffill()
    df_master['temp_measured'] = df_master['temp_measured'].fillna(df_master['t'])

    df_master['temp_lag_1d'] = df_master.groupby('stack_id')['temp_measured'].shift(1)
    df_master['temp_ror'] = df_master['temp_measured'] - df_master['temp_lag_1d']
    df_master['temp_ror'] = df_master['temp_ror'].fillna(0)
    
    df_master = df_master.dropna(subset=['t']).reset_index(drop=True)

    df_master['avg_temp_3d'] = df_master.groupby('stack_id')['temp_measured'].transform(lambda x: x.rolling(window=3, min_periods=1).mean())
    df_master['avg_temp_7d'] = df_master.groupby('stack_id')['temp_measured'].transform(lambda x: x.rolling(window=7, min_periods=1).mean())
    df_master['avg_ror_7d'] = df_master.groupby('stack_id')['temp_ror'].transform(lambda x: x.rolling(window=7, min_periods=1).mean())
    
    df_master['coal_type'] = df_master['coal_type'].astype('category').cat.codes
    
    X = df_master.drop(columns=['date', 'stack_id', 'temp_lag_1d', 'coord_x', 'coord_y'])
    
    return df_master, X

def calculate_temporal_accuracy(df_predictions: pd.DataFrame, df_fires_actual: pd.DataFrame) -> float:
    """
    Считает процент фактических пожаров, для которых был сделан прогноз 
    в окне [3 дня ДО пожара, 1 день ДО пожара].
    """
    
    df_risk_predictions = df_predictions[df_predictions['probability'] > 0.60].copy()
    
    total_fires = len(df_fires_actual)
    successful_predictions = 0
    
    if total_fires == 0:
        return 0.0

    for _, fire_row in df_fires_actual.iterrows():
        stack_id = fire_row['Штабель']
        fire_date = fire_row['fire_date']
        
        start_window = fire_date - pd.Timedelta(days=3)
        end_window = fire_date - pd.Timedelta(days=1)
        
        match = df_risk_predictions[
            (df_risk_predictions['stack_id'] == stack_id) & 
            (df_risk_predictions['date'] >= start_window) &
            (df_risk_predictions['date'] <= end_window)
        ]
        
        if not match.empty:
            successful_predictions += 1
            
    return successful_predictions / total_fires


app = FastAPI(
    title="Coal Fire Predictor API",
    description="API для прогнозирования самовозгорания угля.",
    version="1.0"
)

model = CatBoostClassifier()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
try:
    if os.path.exists(model_path):
        model.load_model(model_path)
    else:
        print("Файл модели не найден. Запустите train_model.py.")
except Exception as e:
    raise RuntimeError(f"Ошибка загрузки CatBoost: {e}")


@app.get("/")
def read_root():
    return {"status": "Server is running", "model_loaded": os.path.exists(model_path)}

@app.post("/predict_data", response_model=List[Dict[str, Any]])
async def predict_full_dataset(
    weather_file: UploadFile = File(..., alias="weather_data"),
    supplies_file: UploadFile = File(..., alias="supplies_data"),
    temperature_file: UploadFile = File(..., alias="temperature_data")
):
    """
    Загружает 3 файла, делает препроцессинг и прогноз на каждый день. 
    Возвращает данные о днях с вероятностью риска > 0.4.
    """
    try:
        df_weather = pd.read_csv(io.StringIO((await weather_file.read()).decode('utf-8')))
        df_supplies = pd.read_csv(io.StringIO((await supplies_file.read()).decode('utf-8')))
        df_temp = pd.read_csv(io.StringIO((await temperature_file.read()).decode('utf-8')))
        
        df_master, X = load_data_from_files(df_weather, df_supplies, df_temp)

        predictions_proba = model.predict_proba(X)
        df_master['probability'] = predictions_proba[:, 1]
        
        PREDICTIONS_CACHE['last_predictions'] = df_master.copy()
        
        df_output = df_master[df_master['probability'] > 0.4].copy() 
        
        df_output['date_str'] = df_output['date'].dt.strftime('%Y-%m-%d')
        
        return df_output[['stack_id', 'date_str', 'probability']].to_dict('records')

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка обработки или прогнозирования: {e}")
    
@app.get("/stack_details/{stack_id}/{date_str}", response_model=Dict[str, Any])
async def get_stack_details(stack_id: int, date_str: str):
    """
    Возвращает детальную информацию для карточки штабеля по ID и дате.
    """
    if 'last_predictions' not in PREDICTIONS_CACHE:
        raise HTTPException(status_code=400, detail="Сначала выполните прогноз через /predict_data.")
    
    df = PREDICTIONS_CACHE['last_predictions']
    
    try:
        date_dt = pd.to_datetime(date_str).normalize()
        
        result = df[
            (df['stack_id'] == stack_id) & 
            (df['date'] == date_dt)
        ]
        
        if result.empty:
            raise HTTPException(status_code=404, detail=f"Данные для штабеля {stack_id} на дату {date_str} не найдены.")
            
        data = result.iloc[0]
        
        card_data = format_card_data(data)
        
        return card_data
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка получения деталей штабеля: {e}")
    
@app.get("/list_all_cards", response_model=List[Dict[str, Any]])
async def list_all_cards():
    """
    ВОЗВРАЩАЕТ СПИСОК УНИКАЛЬНЫХ ШТАБЕЛЕЙ с агрегированными данными, включая X и Y.
    """
    if 'last_predictions' not in PREDICTIONS_CACHE:
        raise HTTPException(status_code=400, detail="Сначала выполните прогноз через /predict_data.")

    df = PREDICTIONS_CACHE['last_predictions'].copy()
    
    if df.empty:
        return []

    df['is_risk'] = (df['probability'] > 0.60).astype(int)
    risk_summary = df.groupby('stack_id').agg(
        total_risk_days=('is_risk', 'sum'),
        total_days=('date', 'size') 
    ).reset_index()
    
    idx_max_prob = df.groupby('stack_id')['probability'].idxmax()
    df_max_risk = df.loc[idx_max_prob].reset_index(drop=True)
    
    df_final = pd.merge(df_max_risk, risk_summary, on='stack_id', how='left')

    card_list = []
    for index, row in df_final.iterrows():
        probability = row['probability']
        status = "В зоне высокого риска" if probability > 0.60 else "Норма"
        
        card_list.append({
            "Номер штабеля": int(row['stack_id']),
            "Тип угля": row['coal_type'],
            "Текущий статус (Макс. риск)": status,
            "Макс. вероятность риска (%)": f"{probability * 100:.2f}%",
            "Макс. вероятность риска (RAW)": float(probability), 
            "Дата самого высокого риска": row['date'].strftime('%Y-%m-%d'),
            "Общее количество дней в зоне риска": int(row['total_risk_days']),
            "Общее количество дней существования": int(row['total_days']), 
            "Макс. температура (на дату макс. риска)": f"{row['temp_measured']:.2f}°C",
            "Координата X": float(row['coord_x']), 
            "Координата Y": float(row['coord_y']) 
        })
        
    return card_list

@app.get("/risk_calendar_dates", response_model=Dict[str, List[str]])
async def get_risk_calendar_dates():
    """
    Возвращает список всех дат, для которых хотя бы один штабель имеет 
    вероятность риска > 0.60.
    
    Формат ответа: {"stack_id": ["YYYY-MM-DD", "YYYY-MM-DD", ...]}
    """
    if 'last_predictions' not in PREDICTIONS_CACHE:
        raise HTTPException(status_code=400, detail="Сначала выполните прогноз через /predict_data.")
    
    df = PREDICTIONS_CACHE['last_predictions'].copy()
    df_risk = df[df['probability'] > 0.60].copy()
    
    if df_risk.empty:
        return {}
        
    df_risk['date_str'] = df_risk['date'].dt.strftime('%Y-%m-%d')
    
    risk_dates = df_risk.groupby('stack_id')['date_str'].apply(list).to_dict()
    
    # Преобразуем ключи stack_id (int) в str для соответствия JSON
    return {str(k): v for k, v in risk_dates.items()}

@app.post("/calculate_metrics", response_model=Dict[str, Any])
async def calculate_metrics(fires_file: UploadFile = File(..., alias="fires_actual_data")):
    """
    Загружает файл с фактическими пожарами (fires.csv) и сравнивает с прогнозом 
    из последнего запроса /predict_data.
    """
    if 'last_predictions' not in PREDICTIONS_CACHE:
        raise HTTPException(status_code=400, detail="Сначала выполните прогноз через /predict_data.")
        
    df_predictions = PREDICTIONS_CACHE['last_predictions'].copy()
    
    try:
        df_fires_actual = pd.read_csv(io.StringIO((await fires_file.read()).decode('utf-8')))
        df_fires_actual['fire_date'] = pd.to_datetime(df_fires_actual['Дата начала']).dt.normalize()
        
        df_predictions['target_fire'] = 0
        
        # (3 дня до пожара)
        for _, row in df_fires_actual.iterrows():
            stack = row['Штабель']
            f_date = row['fire_date']
            
            mask = (
                (df_predictions['stack_id'] == stack) & 
                (df_predictions['date'] >= (f_date - pd.Timedelta(days=3))) &
                (df_predictions['date'] <= (f_date - pd.Timedelta(days=1))) 
            )
            df_predictions.loc[mask, 'target_fire'] = 1

        df_merged = df_predictions[df_predictions['target_fire'].notnull()]
        
        # Применение порога 0.60 для бинарной классификации
        df_merged['prediction_class'] = (df_merged['probability'] > 0.60).astype(int)
        
        # Расчет ключевой метрики
        temporal_accuracy = calculate_temporal_accuracy(df_predictions, df_fires_actual)
        
        report = classification_report(df_merged['target_fire'], df_merged['prediction_class'], output_dict=True, zero_division=0)
        auc_roc = roc_auc_score(df_merged['target_fire'], df_merged['probability'])
        
        metrics = {
            "accuracy": round(report['accuracy'], 4),
            "f1_score_risk": round(report['1']['f1-score'], 4),
            "precision_risk": round(report['1']['precision'], 4),
            "recall_risk": round(report['1']['recall'], 4),
            "auc_roc": round(auc_roc, 4),
            "total_risk_periods": int(df_merged['target_fire'].sum()),
            
            "temporal_accuracy_70_percent": round(temporal_accuracy, 4) 
        }
        
        return metrics
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка расчета метрик: {e}")
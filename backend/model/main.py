import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from catboost import CatBoostClassifier
from sklearn.metrics import classification_report, roc_auc_score
import os
import io
from datetime import datetime
from typing import List, Dict, Any

script_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(script_dir, "catboost_model.cbm")

PREDICTIONS_CACHE = {} 

def load_data_from_files(df_weather_raw, df_supplies_raw, df_temp_raw):
    df_supplies_raw['Start_Date'] = pd.to_datetime(df_supplies_raw['ВыгрузкаНаСклад']).dt.normalize()
    df_supplies_raw['End_Date'] = pd.to_datetime(df_supplies_raw['ПогрузкаНаСудно']).dt.normalize()
    
    stack_daily_rows = []
    for _, row in df_supplies_raw.iterrows():
        end_date = row['End_Date'] if pd.notnull(row['End_Date']) else pd.to_datetime("2021-12-31")
        start_date = row['Start_Date']
        
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        for date in date_range:
            stack_daily_rows.append({
                'stack_id': row['Штабель'],
                'date': date.normalize(),
                'coal_type': row.get('Наим. ЕТСНГ', 'Unknown'),
                'initial_amount': row.get('На склад, тн', 0),
                'coal_age_days': (date.normalize() - start_date).days 
            })
            
    df_master = pd.DataFrame(stack_daily_rows)
    
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
    df_master['temp_ror'] = df_master['temp_measured'] - df_master['temp_lag_1d'] # RoR
    df_master['temp_ror'] = df_master['temp_ror'].fillna(0)
    
    df_master = df_master.dropna(subset=['t']).reset_index(drop=True)
    
    X = df_master.drop(columns=['date', 'stack_id', 'temp_lag_1d'])

    return df_master, X

app = FastAPI(
    title="Coal Fire Predictor API",
    description="API для прогнозирования самовозгорания угля.",
    version="1.0"
)

model = CatBoostClassifier()
try:
    if os.path.exists(model_path):
        model.load_model(model_path)
        print("Модель CatBoost успешно загружена.")
    else:
        print("Файл модели не найден. Запустите train_model.py.")
except Exception as e:
    raise RuntimeError(f"Ошибка загрузки CatBoost: {e}")

@app.post("/predict_data", response_model=List[Dict[str, Any]])
async def predict_full_dataset(
    weather_file: UploadFile = File(..., alias="weather_data"),
    supplies_file: UploadFile = File(..., alias="supplies_data"),
    temperature_file: UploadFile = File(..., alias="temperature_data")
):
    """
    Загружает 3 файла, делает препроцессинг, прогноз на каждый день 
    и сохраняет результат в кэш. Возвращает данные для календаря.
    """
    try:
        df_weather = pd.read_csv(io.StringIO((await weather_file.read()).decode('utf-8')))
        df_supplies = pd.read_csv(io.StringIO((await supplies_file.read()).decode('utf-8')))
        df_temp = pd.read_csv(io.StringIO((await temperature_file.read()).decode('utf-8')))
        
        df_master, X = load_data_from_files(df_weather, df_supplies, df_temp)

        predictions_proba = model.predict_proba(X)
        df_master['probability'] = predictions_proba[:, 1]
        
        PREDICTIONS_CACHE['last_predictions'] = df_master.copy()
        
        df_output = df_master[df_master['probability'] > 0.4] 
        
        df_output['date_str'] = df_output['date'].dt.strftime('%Y-%m-%d')
        
        return df_output[['stack_id', 'date_str', 'probability']].to_dict('records')

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка обработки или прогнозирования: {e}")

@app.post("/calculate_metrics", response_model=Dict[str, Any])
async def calculate_metrics(fires_file: UploadFile = File(..., alias="fires_actual_data")):
    """
    Загружает файл с фактическими пожарами (fires.csv) и сравнивает с прогнозом.
    """
    if 'last_predictions' not in PREDICTIONS_CACHE:
        raise HTTPException(status_code=400, detail="Сначала выполните прогноз через /predict_data.")
        
    df_predictions = PREDICTIONS_CACHE['last_predictions'].copy()
    
    try:
        df_fires_actual = pd.read_csv(io.StringIO((await fires_file.read()).decode('utf-8')))
        df_fires_actual['fire_date'] = pd.to_datetime(df_fires_actual['Дата начала']).dt.normalize()
        
        df_predictions['target_fire'] = 0
        
        for _, row in df_fires_actual.iterrows():
            stack = row['Штабель']
            f_date = row['fire_date']
            
            mask = (
                (df_predictions['stack_id'] == stack) & 
                (df_predictions['date'] >= (f_date - pd.Timedelta(days=7))) &
                (df_predictions['date'] <= f_date)
            )
            df_predictions.loc[mask, 'target_fire'] = 1

        df_merged = df_predictions[df_predictions['target_fire'].notnull()]
        
        df_merged['prediction_class'] = (df_merged['probability'] > 0.5).astype(int)
        
        report = classification_report(df_merged['target_fire'], df_merged['prediction_class'], output_dict=True, zero_division=0)
        auc_roc = roc_auc_score(df_merged['target_fire'], df_merged['probability'])
        
        metrics = {
            "accuracy": round(report['accuracy'], 4),
            "f1_score_risk": round(report['1']['f1-score'], 4),
            "precision_risk": round(report['1']['precision'], 4),
            "recall_risk": round(report['1']['recall'], 4),
            "auc_roc": round(auc_roc, 4),
            "total_risk_periods": int(df_merged['target_fire'].sum())
        }
        
        return metrics

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка расчета метрик: {e}")

@app.get("/")
def read_root():
    return {"status": "Server is running", "model_loaded": os.path.exists(model_path)}
import pytest
import pandas as pd
import io
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from main import app, load_data_from_files, model, calculate_temporal_accuracy

client = TestClient(app)


MOCK_FIRES_CSV = """Штабель,Дата начала
1,2021-01-05
2,2021-01-04
"""

# Штабель 1: существует с 2021-01-01 по 2021-01-03 (3 дня)
# Штабель 2: существует с 2021-01-03 по 2021-01-04 (2 дня)
MOCK_SUPPLIES_CSV = """Штабель,ВыгрузкаНаСклад,ПогрузкаНаСудно,Наим. ЕТСНГ,На склад, тн
1,2021-01-01,2021-01-03,Тип А,1000
2,2021-01-03,2021-01-04,Тип Б,500
"""

MOCK_WEATHER_CSV = """date,t,wind_dir,v_avg,humidity
2021-01-01,10.0,90,5,80
2021-01-02,12.0,95,6,75
2021-01-03,15.0,100,7,70
2021-01-04,18.0,110,8,65
"""

# Температура (ключевые точки для RoR и заполнения пропусков)
# Штабель 1: 10->15->15
# Штабель 2: NA->20
MOCK_TEMP_CSV = """Дата акта,Штабель,Максимальная температура
2021-01-01,1,10.0
2021-01-02,1,15.0
2021-01-04,2,20.0
"""

def get_mock_dfs():
    df_weather = pd.read_csv(io.StringIO(MOCK_WEATHER_CSV))
    df_supplies = pd.read_csv(io.StringIO(MOCK_SUPPLIES_CSV))
    df_temp = pd.read_csv(io.StringIO(MOCK_TEMP_CSV))
    return df_weather, df_supplies, df_temp


# 2. тесты функций преобразования данных


def test_load_data_from_files_structure():
    """Проверяет, что функция load_data_from_files создает корректный DataFrame и признаки."""
    df_weather, df_supplies, df_temp = get_mock_dfs()
    df_master, X = load_data_from_files(df_weather, df_supplies, df_temp)

    assert len(df_master) == 5

    required_cols = [
        'coal_age_days', 'temp_measured', 'temp_ror', 
        'avg_temp_3d', 'avg_ror_7d', 'coord_x', 'coord_y'
    ]
    for col in required_cols:
        assert col in df_master.columns
        
    assert df_master['stack_id'].dtype == 'int64'

def test_load_data_from_files_feature_values():
    """Проверяет корректность расчета ключевых признаков (Age, RoR, Imputation)."""
    df_weather, df_supplies, df_temp = get_mock_dfs()
    df_master, X = load_data_from_files(df_weather, df_supplies, df_temp)

    # 1. Проверка возраста угля (coal_age_days)
    # Штабель 1, дата 2021-01-03, начало 2021-01-01. Возраст должен быть 2 дня.
    age = df_master[(df_master['stack_id'] == 1) & (df_master['date'] == pd.to_datetime('2021-01-03'))]['coal_age_days'].iloc[0]
    assert age == 2

    # 2. Проверка RoR (Rate of Rise)
    # Штабель 1: 2021-01-02. Temp 15.0. Lag Temp 10.0. RoR = 5.0
    ror = df_master[(df_master['stack_id'] == 1) & (df_master['date'] == pd.to_datetime('2021-01-02'))]['temp_ror'].iloc[0]
    assert ror == 5.0

    # 3. Проверка Imputation (заполнение пропусков)
    # Штабель 2: 2021-01-03. В MOCK_TEMP нет данных. Должно быть заполнено температурой воздуха (15.0).
    imputed_temp = df_master[(df_master['stack_id'] == 2) & (df_master['date'] == pd.to_datetime('2021-01-03'))]['temp_measured'].iloc[0]
    assert imputed_temp == 15.0

    coord_x = df_master['coord_x'].iloc[0]
    assert 44.7 <= coord_x <= 44.8
    assert coord_x != 100.0



# 3. тесты эндов


def test_api_root():
    """Проверяет доступность корневого эндпоинта."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Server is running" in response.json()['status']

def test_api_predict_data_success():
    """Проверяет успешное выполнение прогноза."""
    files = {
        'weather_data': ('weather.csv', MOCK_WEATHER_CSV, 'text/csv'),
        'supplies_data': ('supplies.csv', MOCK_SUPPLIES_CSV, 'text/csv'),
        'temperature_data': ('temperature.csv', MOCK_TEMP_CSV, 'text/csv'),
    }
    
    if not model.is_fitted():
        pytest.skip("Модель CatBoost не загружена. Прогноз невозможен.")
        return

    response = client.post("/predict_data", files=files)
    
    assert response.status_code == 200
    
    data = response.json()
    
    assert isinstance(data, list)
    
    if data:
        first_record = data[0]
        assert 'stack_id' in first_record
        assert 'date_str' in first_record
        assert 'probability' in first_record
        assert first_record['probability'] > 0.4 


def test_calculate_temporal_accuracy_logic():
    """
    Проверяет корректность расчета метрики "70% случаев ±2 дня".
    
    Использует моковые данные:
    1. Штабель 1: Пожар 2021-01-05. Окно прогноза: [2021-01-02, 2021-01-04] (3 дня).
    2. Штабель 2: Пожар 2021-01-04. Окно прогноза: [2021-01-01, 2021-01-03] (3 дня).
    """
    # 1. Готовим данные прогноза (должны быть те же, что и в тесте feature_values)
    df_weather, df_supplies, df_temp = get_mock_dfs()
    df_master, X = load_data_from_files(df_weather, df_supplies, df_temp)
    
    # Искусственно добавляем прогнозные вероятности для покрытия окна:
    
    # Штабель 1: Покрытие
    # 2021-01-03 (в окне 2021-01-02 до 2021-01-04) -> УСПЕХ (1)
    df_master.loc[(df_master['stack_id'] == 1) & (df_master['date'] == pd.to_datetime('2021-01-03')), 'probability'] = 0.8
    
    # Штабель 2: Покрытие
    # 2021-01-03 (в окне 2021-01-01 до 2021-01-03) -> УСПЕХ (2)
    df_master.loc[(df_master['stack_id'] == 2) & (df_master['date'] == pd.to_datetime('2021-01-03')), 'probability'] = 0.9
    
    # Искусственно добавляем "Ложную тревогу" (не должна влиять на эту метрику)
    df_master.loc[(df_master['stack_id'] == 1) & (df_master['date'] == pd.to_datetime('2021-01-01')), 'probability'] = 0.9 
    
    # Искусственно добавляем "Пропуск (Miss)" (вероятность < 0.4)
    df_master.loc[(df_master['stack_id'] == 2) & (df_master['date'] == pd.to_datetime('2021-01-01')), 'probability'] = 0.2

    # 2. Готовим данные о фактических пожарах
    df_fires = pd.read_csv(io.StringIO(MOCK_FIRES_CSV))
    df_fires['fire_date'] = pd.to_datetime(df_fires['Дата начала']).dt.normalize()
    
    # 3. Расчет метрики
    accuracy = calculate_temporal_accuracy(df_master, df_fires)
    
    # Ожидаемый результат: 2 успешных прогноза из 2 фактических пожаров = 1.0 (100%)
    assert accuracy == 1.0
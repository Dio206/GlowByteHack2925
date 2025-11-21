import pandas as pd
import glob
import os
import numpy as np

def load_and_process_data(data_folder="data"):

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_folder_full_path = os.path.join(script_dir, "..", data_folder)

    weather_path = os.path.join(data_folder_full_path, "weather", "weather_data_*.csv")
    weather_files = glob.glob(weather_path)
    if not weather_files:
        raise FileNotFoundError("Не найдены файлы погоды")
    
    df_weather = pd.concat([pd.read_csv(f) for f in weather_files])
    df_weather['date'] = pd.to_datetime(df_weather['date']).dt.normalize()
    df_weather = df_weather.groupby('date').agg({
        't': 'mean', 'wind_dir': 'mean', 'v_avg': 'mean', 'humidity': 'mean'
    }).reset_index()
    print(f"Погода загружена: {len(df_weather)} строк")

    supplies_path = os.path.join(data_folder_full_path, "supplies.csv")
    df_supplies = pd.read_csv(supplies_path)
    df_supplies['Start_Date'] = pd.to_datetime(df_supplies['ВыгрузкаНаСклад']).dt.normalize()
    df_supplies['End_Date'] = pd.to_datetime(df_supplies['ПогрузкаНаСудно']).dt.normalize()

    stack_daily_rows = []
    
    for _, row in df_supplies.iterrows():
        end_date = row['End_Date'] if pd.notnull(row['End_Date']) else pd.to_datetime("2021-12-31")
        start_date = row['Start_Date']
        
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        for date in date_range:
            stack_daily_rows.append({
                'stack_id': row['Штабель'],
                'date': date,
                'coal_type': row.get('Наим. ЕТСНГ', 'Unknown'),
                'initial_amount': row.get('На склад, тн', 0),
 
                'coal_age_days': (date - start_date).days
            })
            
    df_master = pd.DataFrame(stack_daily_rows)
    df_master = df_master.merge(df_weather, on='date', how='left')

    temp_path = os.path.join(data_folder_full_path, "temperature.csv")
    df_temp = pd.read_csv(temp_path)
    df_temp['date'] = pd.to_datetime(df_temp['Дата акта']).dt.normalize()
    df_temp = df_temp.rename(columns={'Штабель': 'stack_id', 'Максимальная температура': 'temp_measured'})
    df_temp = df_temp[['stack_id', 'date', 'temp_measured']].drop_duplicates(subset=['stack_id', 'date'], keep='first')
    
    df_master = df_master.merge(df_temp, on=['stack_id', 'date'], how='left')
    
    df_master['temp_measured'] = df_master.groupby('stack_id')['temp_measured'].ffill()
    df_master['temp_measured'] = df_master['temp_measured'].fillna(df_master['t'])

    df_master['temp_lag_1d'] = df_master.groupby('stack_id')['temp_measured'].shift(1)
    df_master['temp_ror'] = df_master['temp_measured'] - df_master['temp_lag_1d']
    df_master['temp_ror'] = df_master['temp_ror'].fillna(0)
    
    fires_path = os.path.join(data_folder_full_path, "fires.csv")
    df_fires = pd.read_csv(fires_path)
    df_fires['fire_date'] = pd.to_datetime(df_fires['Дата начала']).dt.normalize()
    
    df_master['target_fire'] = 0
    
    for _, row in df_fires.iterrows():
        stack = row['Штабель']
        f_date = row['fire_date']
        
        mask = (
            (df_master['stack_id'] == stack) & 
            (df_master['date'] >= (f_date - pd.Timedelta(days=7))) &
            (df_master['date'] <= f_date)
        )
        df_master.loc[mask, 'target_fire'] = 1

    df_master = df_master.dropna(subset=['t'])
    
    df_master = df_master.drop(columns=['temp_lag_1d'])
    
    print(f"🔥 Готово! Размер итогового датасета: {df_master.shape}")
    return df_master

if __name__ == "__main__":
    try:
        df = load_and_process_data()
        output_path = os.path.join(os.path.dirname(__file__), "..", "data", "training_dataset.csv")
        df.to_csv(output_path, index=False)
      
        print("\nНовые признаки:")
        print(df[['coal_age_days', 'temp_ror']].head())
    except Exception as e:
        print(f"Ошибка: {e}")
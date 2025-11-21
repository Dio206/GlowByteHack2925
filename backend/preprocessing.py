import pandas as pd
import glob
import os
import numpy as np

def load_and_process_data(data_folder="data"):
    print("Начинаем сборку данных...")

    weather_path = os.path.join(data_folder, "weather", "weather_data_*.csv")
    weather_files = glob.glob(weather_path)
    
    if not weather_files:
        raise FileNotFoundError("Не найдены файлы погоды!")

    df_weather = pd.concat([pd.read_csv(f) for f in weather_files])
    df_weather['date'] = pd.to_datetime(df_weather['date']).dt.normalize()
    df_weather = df_weather.groupby('date').agg({
        't': 'mean', 'wind_dir': 'mean', 'v_avg': 'mean', 'humidity': 'mean'
    }).reset_index()
    print(f"✅ Погода загружена: {len(df_weather)} строк")

    supplies_path = os.path.join(data_folder, "supplies.csv")
    df_supplies = pd.read_csv(supplies_path)
    
    df_supplies['Start_Date'] = pd.to_datetime(df_supplies['ВыгрузкаНаСклад'])
    df_supplies['End_Date'] = pd.to_datetime(df_supplies['ПогрузкаНаСудно'])
    
    stack_daily_rows = []
    
    for _, row in df_supplies.iterrows():
        end_date = row['End_Date'] if pd.notnull(row['End_Date']) else pd.to_datetime("2021-12-31")
        
        date_range = pd.date_range(start=row['Start_Date'], end=end_date, freq='D')
        
        for date in date_range:
            stack_daily_rows.append({
                'stack_id': row['Штабель'],
                'date': date,
                'coal_type': row.get('Наим. ЕТСНГ', 'Unknown'), # Марка угля
                'initial_amount': row.get('На склад, тн', 0) # Объем
            })
            
    df_master = pd.DataFrame(stack_daily_rows)
    print(f"Скелет таблицы создан: {len(df_master)} строк (дней жизни штабелей)")

    df_master = df_master.merge(df_weather, on='date', how='left')

    temp_path = os.path.join(data_folder, "temperature.csv")
    df_temp = pd.read_csv(temp_path)
    df_temp['date'] = pd.to_datetime(df_temp['Дата акта'])
    df_temp = df_temp.rename(columns={'Штабель': 'stack_id', 'Максимальная температура': 'temp_measured'})
    
    df_master = df_master.merge(df_temp[['stack_id', 'date', 'temp_measured']], on=['stack_id', 'date'], how='left')
    
    df_master['temp_measured'] = df_master.groupby('stack_id')['temp_measured'].ffill()
    
   
    df_master['temp_measured'] = df_master['temp_measured'].fillna(df_master['t'])

    fires_path = os.path.join(data_folder, "fires.csv")
    df_fires = pd.read_csv(fires_path)
    df_fires['fire_date'] = pd.to_datetime(df_fires['Дата начала'])
    
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
    
    return df_master

if __name__ == "__main__":

    try:
        df = load_and_process_data()
        print(df.head())
        print("\nПример строки с пожаром:")
        print(df[df['target_fire'] == 1].head(1))
        
        df.to_csv("data/training_dataset.csv", index=False)
    except Exception as e:
        print(f"Ошибка: {e}")
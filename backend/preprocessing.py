import pandas as pd
import glob
import os
import numpy as np

def load_and_process_data(data_folder="data"):
    print("⏳ Начинаем сборку данных...")

    # --- 1. ЗАГРУЗКА ПОГОДЫ (Все года сразу) ---
    weather_path = os.path.join(data_folder, "weather", "weather_data_*.csv")
    weather_files = glob.glob(weather_path)
    
    if not weather_files:
        raise FileNotFoundError("❌ Не найдены файлы погоды!")

    df_weather = pd.concat([pd.read_csv(f) for f in weather_files])
    # Приводим дату к datetime и убираем время, оставляем только дату (для матчинга по дням)
    df_weather['date'] = pd.to_datetime(df_weather['date']).dt.normalize()
    # Группируем по дням (берем среднее), если вдруг есть почасовые данные
    df_weather = df_weather.groupby('date').agg({
        't': 'mean', 'wind_dir': 'mean', 'v_avg': 'mean', 'humidity': 'mean'
    }).reset_index()
    print(f"✅ Погода загружена: {len(df_weather)} строк")

    # --- 2. ЗАГРУЗКА СПИСКА ШТАБЕЛЕЙ (Supplies) ---
    supplies_path = os.path.join(data_folder, "supplies.csv")
    df_supplies = pd.read_csv(supplies_path)
    
    # Превращаем даты в формат datetime
    df_supplies['Start_Date'] = pd.to_datetime(df_supplies['ВыгрузкаНаСклад'])
    df_supplies['End_Date'] = pd.to_datetime(df_supplies['ПогрузкаНаСудно'])
    
    # --- 3. СОЗДАНИЕ СКЕЛЕТА (Каждый день жизни штабеля) ---
    # Это самая важная часть: разворачиваем диапазоны дат в строки
    stack_daily_rows = []
    
    for _, row in df_supplies.iterrows():
        # Если дата отгрузки пустая, считаем что уголь лежит до сегодня (или до конца 2021)
        end_date = row['End_Date'] if pd.notnull(row['End_Date']) else pd.to_datetime("2021-12-31")
        
        # Создаем диапазон дат для этого штабеля
        date_range = pd.date_range(start=row['Start_Date'], end=end_date, freq='D')
        
        for date in date_range:
            stack_daily_rows.append({
                'stack_id': row['Штабель'],
                'date': date,
                'coal_type': row.get('Наим. ЕТСНГ', 'Unknown'), # Марка угля
                'initial_amount': row.get('На склад, тн', 0) # Объем
            })
            
    df_master = pd.DataFrame(stack_daily_rows)
    print(f"✅ Скелет таблицы создан: {len(df_master)} строк (дней жизни штабелей)")

    # --- 4. ДОБАВЛЯЕМ ПОГОДУ ---
    df_master = df_master.merge(df_weather, on='date', how='left')

    # --- 5. ДОБАВЛЯЕМ ТЕМПЕРАТУРУ ВНУТРИ (Temperature) ---
    temp_path = os.path.join(data_folder, "temperature.csv")
    df_temp = pd.read_csv(temp_path)
    df_temp['date'] = pd.to_datetime(df_temp['Дата акта'])
    df_temp = df_temp.rename(columns={'Штабель': 'stack_id', 'Максимальная температура': 'temp_measured'})
    
    # Мерджим температуру
    df_master = df_master.merge(df_temp[['stack_id', 'date', 'temp_measured']], on=['stack_id', 'date'], how='left')
    
    # ВАЖНО: Температуру меряют редко. Заполняем пропуски предыдущим значением (ffill)
    # Для каждого штабеля отдельно!
    df_master['temp_measured'] = df_master.groupby('stack_id')['temp_measured'].ffill()
    
    # Если в начале вообще не было замеров, заполняем температурой воздуха (грубая эвристика, но лучше чем 0)
    df_master['temp_measured'] = df_master['temp_measured'].fillna(df_master['t'])

    # --- 6. СОЗДАЕМ ЦЕЛЕВУЮ ПЕРЕМЕННУЮ (TARGET) ---
    fires_path = os.path.join(data_folder, "fires.csv")
    df_fires = pd.read_csv(fires_path)
    df_fires['fire_date'] = pd.to_datetime(df_fires['Дата начала'])
    
    # По умолчанию пожара нет
    df_master['target_fire'] = 0
    
    # Проставляем 1, если пожар произошел
    for _, row in df_fires.iterrows():
        stack = row['Штабель']
        f_date = row['fire_date']
        
        # Мы хотим предсказать пожар ЗАРАНЕЕ (например, за 7 дней до события риск высокий)
        # Ставим "1" на все дни за неделю до пожара
        mask = (
            (df_master['stack_id'] == stack) & 
            (df_master['date'] >= (f_date - pd.Timedelta(days=7))) &
            (df_master['date'] <= f_date)
        )
        df_master.loc[mask, 'target_fire'] = 1

    # Удаляем строки, где нет погоды (совсем старые или будущие даты без данных)
    df_master = df_master.dropna(subset=['t'])
    
    print(f"🔥 Готово! Размер итогового датасета: {df_master.shape}")
    return df_master

if __name__ == "__main__":
    # Для теста запускаем скрипт напрямую
    try:
        df = load_and_process_data()
        print(df.head())
        print("\nПример строки с пожаром:")
        print(df[df['target_fire'] == 1].head(1))
        
        # Сохраним, чтобы вы могли глазами посмотреть в Excel
        df.to_csv("data/training_dataset.csv", index=False)
        print("\n💾 Сохранено в data/training_dataset.csv")
    except Exception as e:
        print(f"Ошибка: {e}")
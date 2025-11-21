import pandas as pd
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import os

def train():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "data", "training_dataset.csv")
    
    if not os.path.exists(data_path):
        print("Файл данных не найден")
        return

    df = pd.read_csv(data_path)
    X = df.drop(columns=['target_fire', 'date', 'stack_id']) 
    y = df['target_fire']

    cat_features = ['coal_type']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=True)

    print(f"🧠 Начинаем обучение на {len(X_train)} строках...")

    # Создаем и обучаем модель
    model = CatBoostClassifier(
        iterations=500,          # Сколько раз модель пройдет по данным
        learning_rate=0.1,       # С какой скоростью учиться
        depth=6,                 # Глубина "дерева решений"
        loss_function='Logloss', # Функция потерь для классификации
        verbose=100              # Выводить отчет каждые 100 шагов
    )

    model.fit(X_train, y_train, cat_features=cat_features, eval_set=(X_test, y_test))

    print("\nРезультаты на тестовых данных:")
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred))
    print(f"AUC-ROC Score: {roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]):.4f}")

    model_path = os.path.join(script_dir, "catboost_model.cbm")
    model.save_model(model_path)
    print(f"\n💾 Модель сохранена в: {model_path}")

if __name__ == "__main__":
    train()
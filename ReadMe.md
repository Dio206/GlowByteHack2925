
<p align="center">
  <img src="https://img.shields.io/badge/Model_Accuracy-96%25-brightgreen?style=for-the-badge&logo=pytorch" alt="Accuracy Badge">
  <img src="https://img.shields.io/badge/AUC_ROC-0.98-blue?style=for-the-badge&logo=scikitlearn" alt="AUC-ROC Badge">
</p>

Прогноз самовозгорания угля (GlowByte Hackathon)

Проект представляет собой комплексное решение для прогнозирования риска самовозгорания угля на открытых складах. Решение включает в себя модель машинного обучения CatBoost, развернутую через FastAPI сервер. (че нибудь про фронт тоже потом добавьте умоляю)

Инструкция по запуску Бэка

1. Создайте окружение и запустите его
python -m venv myenv
myenv\Scripts\activate

2. Перейдите в папку `backend` и установите все необходимые библиотеки:

cd backend
pip install -r requirements.txt


2. Перейдите в папку model и запустите сервер
cd model
py -m uvicorn main:app --reload


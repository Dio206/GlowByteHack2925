import { useState } from "react";

export const PredictPage = () => {
    const [weatherFile, setWeatherFile] = useState<File | null>(null);
    const [suppliesFile, setSuppliesFile] = useState<File | null>(null);
    const [temperatureFile, setTemperatureFile] = useState<File | null>(null);
    const [result, setResult] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async () => {
        if (!weatherFile || !suppliesFile || !temperatureFile) {
            setError("Все три файла должны быть выбраны");
            return;
        }

        const formData = new FormData();
        formData.append("weather_data", weatherFile);
        formData.append("supplies_data", suppliesFile);
        formData.append("temperature_data", temperatureFile);

        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const res = await fetch("http://localhost:8000/predict_data", {
                method: "POST",
                body: formData,
            });

            if (!res.ok) {
                throw new Error(`Ошибка ${res.status}`);
            }

            const data = await res.json();
            setResult(data);
        } catch (err: any) {
            console.error(err);
            setError(err.message || "Неизвестная ошибка");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ padding: 20 }}>
            <h1>Прогноз самовозгорания угля</h1>

            <div>
                <label>
                    Weather Data (CSV):
                    <input
                        type="file"
                        accept=".csv"
                        onChange={(e) => setWeatherFile(e.target.files?.[0] || null)}
                    />
                </label>
            </div>

            <div>
                <label>
                    Supplies Data (CSV):
                    <input
                        type="file"
                        accept=".csv"
                        onChange={(e) => setSuppliesFile(e.target.files?.[0] || null)}
                    />
                </label>
            </div>

            <div>
                <label>
                    Temperature Data (CSV):
                    <input
                        type="file"
                        accept=".csv"
                        onChange={(e) => setTemperatureFile(e.target.files?.[0] || null)}
                    />
                </label>
            </div>

            <button onClick={handleSubmit} disabled={loading} style={{ marginTop: 10 }}>
                {loading ? "Загрузка..." : "Отправить"}
            </button>

            {error && <div style={{ color: "red", marginTop: 10 }}>Ошибка: {error}</div>}

            {result && (
                <div style={{ marginTop: 20 }}>
                    <h2>Результат:</h2>
                    <pre style={{ maxHeight: 400, overflow: "auto" }}>
            {JSON.stringify(result, null, 2)}
          </pre>
                </div>
            )}
        </div>
    );
};

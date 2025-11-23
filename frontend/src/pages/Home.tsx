import { useEffect, useState } from 'react';

export const Home = () => {
    const [prediction, setPrediction] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    const fetchData = async () => {
        try {
            const res = await fetch('http://localhost:8000/predict_data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    startDate: "2025-11-23",
                    endDate: "2025-11-30",
                    stackIds: [1, 2, 3]
                }),
            });

            if (!res.ok) throw new Error(`Ошибка ${res.status}`);

            const data = await res.json();
            setPrediction(data);
            setError(null);
        } catch (err: any) {
            console.error('Ошибка загрузки данных:', err);
            setError(err.message || 'Неизвестная ошибка');
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    if (error) return <div className="home-error">Ошибка: {error}</div>;
    if (!prediction) return <p>Загрузка данных...</p>;

    return (
        <div className="home">
            <pre>{JSON.stringify(prediction, null, 2)}</pre>
        </div>
    );
};

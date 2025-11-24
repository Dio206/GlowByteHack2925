import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Map.scss";

interface StackData {
    "Номер штабеля": number;
    "Тип угля": string;
    "Текущий статус (Макс. риск)"?: string;
    "Макс. вероятность риска (%)"?: string;
    "Макс. температура (на дату макс. риска)"?: string;
    "Дата самого высокого риска"?: string;
    "Общее количество дней в зоне риска"?: number;
    "Координата X": number;
    "Координата Y": number;
}

interface StackPoint extends StackData {
    x: number;
    y: number;
}

const Map: React.FC = () => {
    const navigate = useNavigate();
    const [stacks, setStacks] = useState<StackPoint[]>([]);
    const [error, setError] = useState<string | null>(null);

    const LAT_MIN = 44.7;
    const LAT_MAX = 44.8;
    const LON_MIN = 37.7;
    const LON_MAX = 37.8;

    const normalize = (value: number, min: number, max: number) => {
        return ((value - min) / (max - min)) * 100;
    };

    const getStatusColor = (status?: string) => {
        switch (status?.toLowerCase()) {
            case "норма":
                return "#57e857";
            case "в зоне высокого риска":
                return "#f15151";
            default:
                return "#888";
        }
    };

    useEffect(() => {
        const fetchStacks = async () => {
            try {
                const res = await fetch("http://localhost:8000/list_all_cards"); // <-- правильный эндпоинт
                if (!res.ok) throw new Error(`Ошибка ${res.status}`);
                const data: StackData[] = await res.json();

                // Преобразуем реальные координаты в проценты для CSS
                const dataWithPercent: StackPoint[] = data.map((s) => ({
                    ...s,
                    x: 100 - normalize(s["Координата X"], LAT_MIN, LAT_MAX), // верх = 0%
                    y: normalize(s["Координата Y"], LON_MIN, LON_MAX),       // левый край = 0%
                }));

                setStacks(dataWithPercent);
                setError(null);
            } catch (err: any) {
                console.error("Ошибка загрузки точек:", err);
                setError("Не удалось загрузить точки.");
                setStacks([]);
            }
        };

        fetchStacks();
    }, []);

    return (
        <div className="map-container">
            <img src="/russia.svg" alt="Карта России" className="map-image" />
            {error && <div className="map-error">{error}</div>}

            {stacks.map((stack) => (
                <div
                    key={stack["Номер штабеля"]}
                    className="map-point"
                    style={{
                        left: `${stack.y}%`,
                        top: `${stack.x}%`,
                        backgroundColor: getStatusColor(stack["Текущий статус (Макс. риск)"]),
                    }}
                    onClick={() => navigate(`/stack/${stack["Номер штабеля"]}`)}
                    title={`${stack["Тип угля"]} (Штабель ${stack["Номер штабеля"]})`}
                />
            ))}
        </div>
    );
};

export default Map;

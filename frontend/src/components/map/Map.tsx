import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Map.scss";

interface StackData {
    id: number;
    name: string;
    x: number;
    y: number;
}

const Map: React.FC = () => {
    const navigate = useNavigate();
    const [stacks, setStacks] = useState<StackData[]>([]);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchStacks = async () => {
            try {
                const res = await fetch("http://localhost:8000/list_all_points");

                if (!res.ok) {
                    throw new Error(`Ошибка ${res.status}`);
                }

                const data = await res.json();
                setStacks(data);
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
                    key={stack.id}
                    className="map-point"
                    style={{
                        left: `${stack.x}%`,
                        top: `${stack.y}%`,
                    }}
                    onClick={() => navigate(`/stack/${stack.id}`)}
                    title={stack.name}
                ></div>
            ))}
        </div>
    );
};

export default Map;

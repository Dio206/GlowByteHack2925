import { useEffect, useState } from 'react';
import "./Sidebar.scss"
import { Link } from "react-router-dom";
import Calendar from "../calendar/Calendar";

interface StackData {
    "Номер штабеля": number;
    "Тип угля": string;
    "Текущий статус (Макс. риск)": string;
    "Макс. вероятность риска (%)": string;
    "Дата самого высокого риска": string;
    "Общее количество дней в зоне риска": number;
    "Макс. температура (на дату макс. риска)": string;
}

export const Sidebar = () => {
    const [stacks, setStacks] = useState<StackData[]>([]);
    const [error, setError] = useState<string | null>(null);

    const fetchStacks = async () => {
        try {
            const res = await fetch('http://localhost:8000/list_all_cards');

            if (res.status === 400) {
                setStacks([]);
                return;
            }

            if (!res.ok) {
                throw new Error(`Ошибка ${res.status}`);
            }

            const data = await res.json();
            setStacks(data);
            setError(null);

        } catch (err: any) {
            console.error("Ошибка загрузки:", err);
            setError(null);
        }
    };

    useEffect(() => {
        fetchStacks();
    }, []);

    return (
        <div className="sidebar">

            <Link to="/predict">
                <button className="upload-btn">Загрузить файлы</button>
            </Link>

            <div className="stacks">
                {stacks.map((stack) => (
                    <Link
                        to={`/stack/${stack["Номер штабеля"]}`}
                        key={stack["Номер штабеля"]}
                        className="stack-item"
                    >
                        <span>Штабель {stack["Номер штабеля"]}</span>
                        <span
                            className={`status-dot ${
                                stack["Текущий статус (Макс. риск)"].toLowerCase().replace(/\s/g, "-")
                            }`}
                        />
                    </Link>
                ))}
            </div>

            <div className="calendar-section">
                <Calendar/>
            </div>
        </div>
    );
};

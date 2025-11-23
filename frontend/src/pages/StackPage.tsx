import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import type { FireData} from "../types/fire";
import './StackPage.scss';

const StackPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const [stackData, setStackData] = useState<FireData | null>(null);
    const [loading, setLoading] = useState(true);

    const getStatus = (prob: number): FireData['status'] => {
        if (prob >= 0.75) return "Высокий риск";
        if (prob > 0.5) return "Средний риск";
        return "Низкий риск";
    };

    useEffect(() => {
        fetch('http://127.0.0.1:8000/predict_data')
            .then(res => res.json())
            .then((data: any[]) => {
                const stack = data.find(item => String(item.stack_id) === id);
                if (stack) {
                    setStackData({
                        stack_id: String(stack.stack_id),
                        date_str: String(stack.date_str),
                        probability: Number(stack.probability),
                        status: getStatus(Number(stack.probability))
                    });
                } else setStackData(null);
            })
            .catch(err => console.error('Ошибка загрузки данных:', err))
            .finally(() => setLoading(false));
    }, [id]);

    if (loading) return <p>Загрузка...</p>;
    if (!stackData) return (
        <div className="stack-page">
            <Link to="/" className="back-link">← Вернуться на главную</Link>
            <p>Такого штабеля не существует</p>
        </div>
    );

    return (
        <div className="stack-page">
            <Link to="/" className="back-link">← Вернуться на главную</Link>
            <h1>{stackData.stack_id}</h1>
            <p>
                Статус:
                <span
                    className={`status-dot ${stackData.status.replace(/\s+/g, '-').toLowerCase()}`}
                    title={stackData.status}
                ></span>
                {stackData.status}
            </p>
            <p>Вероятность возгорания: {stackData.probability}</p>
            <p>Дата прогноза: {stackData.date_str}</p>
        </div>
    );
};

export default StackPage;

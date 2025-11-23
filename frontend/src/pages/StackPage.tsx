import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import './StackPage.scss';

const riskColorMap: Record<string, string> = {
    "Норма": "#57e857",
    "В зоне высокого риска": "#f15151",
};

const StackPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const [stack, setStack] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch("http://localhost:8000/list_all_cards")
            .then(res => res.json())
            .then((data) => {
                const found = data.find(
                    (item: any) => String(item["Номер штабеля"]) === id
                );
                setStack(found || null);
            })
            .finally(() => setLoading(false));
    }, [id]);

    if (loading) return <p>Загрузка...</p>;
    if (!stack) return <p>Штабель не найден</p>;

    return (
        <div className="stack-page">
            <Link to="/" className="back-link">← Назад</Link>

            <h1>Штабель {stack["Номер штабеля"]}</h1>

            <div className="stack-info-card">
                <div className="info-row">
                    <span className="info-title">Тип угля:</span>
                    <span className="info-value">{stack["Тип угля"]}</span>
                </div>

                <div className="info-row">
                    <span className="info-title">Статус:</span>
                    <span className="info-value status">
                <span
                    className="status-dot"
                    style={{ backgroundColor: riskColorMap[stack["Текущий статус (Макс. риск)"]] }}
                />
                        {stack["Текущий статус (Макс. риск)"]}
            </span>
                </div>

                <div className="info-row">
                    <span className="info-title">Макс. риск:</span>
                    <span className="info-value">{stack["Макс. вероятность риска (%)"]}</span>
                </div>

                <div className="info-row">
                    <span className="info-title">Дата максимального риска:</span>
                    <span className="info-value">{stack["Дата самого высокого риска"]}</span>
                </div>

                <div className="info-row">
                    <span className="info-title">Дней в риске:</span>
                    <span className="info-value">{stack["Общее количество дней в зоне риска"]}</span>
                </div>

                <div className="info-row">
                    <span className="info-title">Макс. температура:</span>
                    <span className="info-value">{stack["Макс. температура (на дату макс. риска)"]}</span>
                </div>
            </div>
        </div>

    );
};

export default StackPage;

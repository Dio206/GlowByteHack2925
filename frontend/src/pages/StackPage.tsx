import React from 'react';
import { Link, useParams } from 'react-router-dom';
import { stacks } from '../data/stacks';
import './StackPage.scss';

const StackPage: React.FC = () => {
    const { id } = useParams();
    const stack = stacks.find(s => s.id === Number(id));

    if (!stack) {
        return <div className="stack-page">
            <Link to="/" className="back-link">
            ← Вернуться на главную
        </Link>
            <p>Такого штабеля не существует</p>
        </div>;
    }

    const riskClass = {
        Низкая: 'risk-low',
        Средняя: 'risk-medium',
        Высокая: 'risk-high',
    }[stack.riskProbability];

    return (
        <div className="stack-page">
            <Link to="/" className="back-link">
                ← Вернуться на главную
            </Link>

            <h1>{stack.name}</h1>
            <p>{stack.description}</p>

            <table className="stack-table">
                <tbody>
                <tr>
                    <th>Параметр</th>
                    <th>Значение</th>
                </tr>
                <tr>
                    <td>Возраст угля</td>
                    <td>{stack.coalAge}</td>
                </tr>
                <tr>
                    <td>Тип угля</td>
                    <td>{stack.coalType}</td>
                </tr>
                <tr>
                    <td>Вероятность риска</td>
                    <td className={riskClass}>{stack.riskProbability}</td>
                </tr>
                <tr>
                    <td>Дата риска</td>
                    <td>{stack.riskDate}</td>
                </tr>
                <tr>
                    <td>Скорость нагрева</td>
                    <td>{stack.heatingRate}</td>
                </tr>
                <tr>
                    <td>Максимальная температура</td>
                    <td>{stack.maxTemperature}</td>
                </tr>
                </tbody>
            </table>
        </div>
    );
};

export default StackPage;

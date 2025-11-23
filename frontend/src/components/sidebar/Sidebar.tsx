import { useEffect, useState } from 'react';

interface StackData {
    id: number;
    name: string;
}

export const Sidebar = () => {
    const [stacks, setStacks] = useState<StackData[]>([]);
    const [error, setError] = useState<string | null>(null);

    const fetchStacks = async () => {
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

            if (!res.ok) {
                throw new Error(`Ошибка ${res.status}`);
            }

            const data = await res.json();
            setStacks(data);
            setError(null);
        } catch (err: any) {
            console.error('Ошибка загрузки данных:', err);
            setError(err.message || 'Неизвестная ошибка');
        }
    };

    useEffect(() => {
        fetchStacks();
    }, []);

    if (error) {
        return <div className="sidebar-error">Ошибка: {error}</div>;
    }

    return (
        <div className="sidebar">
            {stacks.length === 0 ? (
                <p>Данные не загружены</p>
            ) : (
                stacks.map(stack => (
                    <div key={stack.id} className="stack-item">
                        {stack.name}
                    </div>
                ))
            )}
        </div>
    );
};

export interface Stack {
    id: number;
    name: string;
    description: string;
    x: number;
    y: number;
    coalAge: string;
    coalType: string;
    riskProbability: "Низкая" | "Средняя" | "Высокая";
    riskDate: string;
    heatingRate: string;
    maxTemperature: string;
    status: "Низкий риск" | "Средний риск" | "Высокий риск";
}

export const stacks: Stack[] = [
    {
        id: 1,
        name: "Штабель 1",
        description: "Описание штабеля 1",
        x: 20,
        y: 30,
        coalAge: "3 месяца",
        coalType: "Антрацит",
        riskProbability: "Средняя",
        riskDate: "2025-11-28",
        heatingRate: "5 °C/ч",
        maxTemperature: "120 °C",
        status: "Низкий риск",
    },
    {
        id: 2,
        name: "Штабель 2",
        description: "Описание штабеля 2",
        x: 50,
        y: 50,
        coalAge: "6 месяцев",
        coalType: "Бурый уголь",
        riskProbability: "Высокая",
        riskDate: "2025-12-05",
        heatingRate: "7 °C/ч",
        maxTemperature: "140 °C",
        status: "Средний риск",
    },
    {
        id: 3,
        name: "Штабель 3",
        description: "Описание штабеля 3",
        x: 70,
        y: 80,
        coalAge: "1 месяц",
        coalType: "Антрацит",
        riskProbability: "Низкая",
        riskDate: "2025-12-15",
        heatingRate: "4 °C/ч",
        maxTemperature: "110 °C",
        status: "Высокий риск",
    },
];

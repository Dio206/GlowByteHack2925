export interface FireData {
    stack_id: string;
    date_str: string;
    probability: number;
    status: "Низкий риск" | "Средний риск" | "Высокий риск";
}

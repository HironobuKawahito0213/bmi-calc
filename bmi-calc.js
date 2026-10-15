// BMI = 体重(kg) ÷ 身長(m) の2乗
// 判定基準は日本肥満学会の分類に準拠
const CATEGORIES = [
    { max: 18.5, label: "低体重(やせ型)", color: "#2b6cb0" },
    { max: 25,   label: "普通体重",       color: "#2f855a" },
    { max: 30,   label: "肥満(1度)",      color: "#b7791f" },
    { max: 35,   label: "肥満(2度)",      color: "#c05621" },
    { max: 40,   label: "肥満(3度)",      color: "#c53030" },
    { max: Infinity, label: "肥満(4度)",  color: "#9b2c2c" },
];

function judgeCategory(bmi) {
    return CATEGORIES.find(c => bmi < c.max);
}

function showError(message) {
    const error = document.getElementById("error");
    error.textContent = message;
    error.hidden = false;
    document.getElementById("result").hidden = true;
}

function calcBmi() {
    const height = parseFloat(document.getElementById("height").value);
    const weight = parseFloat(document.getElementById("weight").value);

    if (Number.isNaN(height) || Number.isNaN(weight)) {
        showError("身長と体重を数値で入力してください。");
        return;
    }
    if (height <= 0 || weight <= 0) {
        showError("身長と体重は0より大きい値を入力してください。");
        return;
    }
    // cm/m の取り違え防止(50cm未満・300cm超は入力ミスとみなす)
    if (height < 50 || height > 300) {
        showError("身長はcm単位で入力してください(例: 170)。");
        return;
    }

    const heightM = height / 100;
    const bmi = weight / (heightM * heightM);
    const category = judgeCategory(bmi);
    const idealWeight = 22 * heightM * heightM;

    document.getElementById("error").hidden = true;
    const result = document.getElementById("result");
    result.hidden = false;

    document.getElementById("bmi").textContent = bmi.toFixed(1);
    const categoryOutput = document.getElementById("category");
    categoryOutput.textContent = category.label;
    categoryOutput.style.color = category.color;
    document.getElementById("idealWeight").textContent = idealWeight.toFixed(1);
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("calc").addEventListener("click", calcBmi);
    // Enterキーでも計算できるようにする
    for (const id of ["height", "weight"]) {
        document.getElementById(id).addEventListener("keydown", (e) => {
            if (e.key === "Enter") calcBmi();
        });
    }
});

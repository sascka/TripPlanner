const button = document.querySelector("#refresh-weather");
const weatherBox = document.querySelector("#weather-box");

if (button && weatherBox) {
    button.addEventListener("click", async () => {
        const city = weatherBox.dataset.city;
        button.disabled = true;
        button.textContent = "Обновляем...";

        try {
            const response = await fetch(`/api/weather?city=${encodeURIComponent(city)}`);
            const data = await response.json();
            if (!response.ok || !data.ok) {
                weatherBox.innerHTML = `<p class="text-muted mb-0">${data.message || data.error}</p>`;
                return;
            }

            weatherBox.innerHTML = `
                <p class="weather-temp mb-1">${data.temperature} °C</p>
                <p class="mb-1">${data.description}</p>
                <p class="small text-muted mb-0">Ощущается как ${data.feels_like} °C, ветер ${data.wind_speed} м/с</p>
            `;
        } catch (error) {
            weatherBox.innerHTML = '<p class="text-muted mb-0">Не удалось обновить погоду.</p>';
        } finally {
            button.disabled = false;
            button.textContent = "Обновить";
        }
    });
}

const btn = document.querySelector('#refresh-weather');
const box = document.querySelector('#weather-box');

if (btn && box) {
    btn.addEventListener('click', async () => {
        const city = box.dataset.city;
        btn.disabled = true;
        btn.textContent = 'Обновляем...';
        try {
            const res = await fetch(`/api/weather?city=${encodeURIComponent(city)}`);
            const data = await res.json();
            if (!res.ok || !data.ok) {
                box.innerHTML = `<p class='text-muted mb-0'>${data.message || data.error}</p>`;
                return;
            }
            box.innerHTML = `
                <p class='temp mb-1'>${data.temperature} °C</p>
                <p class='mb-1'>${data.description}</p>
                <p class='small text-muted mb-0'>Ощущается как ${data.feels_like} °C, ветер ${data.wind_speed} м/с</p>
            `;
        } catch (error) {
            box.innerHTML = '<p class=\'text-muted mb-0\'>Не удалось обновить погоду.</p>';
        } finally {
            btn.disabled = false;
            btn.textContent = 'Обновить';
        }
    });
}

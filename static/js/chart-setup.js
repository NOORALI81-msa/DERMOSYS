document.addEventListener("DOMContentLoaded", () => {
    // Disease Frequency Chart (Bar Chart)
    const diseaseData = JSON.parse(document.getElementById('diseaseData').textContent);
    const diseaseCtx = document.getElementById('diseaseChart').getContext('2d');
    new Chart(diseaseCtx, {
        type: 'bar',
        data: {
            labels: Object.keys(diseaseData),
            datasets: [{
                label: 'Number of Cases',
                data: Object.values(diseaseData),
                backgroundColor: 'rgba(52, 152, 219, 0.7)',
                borderColor: 'rgba(52, 152, 219, 1)',
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                y: { beginAtZero: true }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });

    // Gender Distribution Chart (Doughnut Chart)
    const genderData = JSON.parse(document.getElementById('genderData').textContent);
    const genderCtx = document.getElementById('genderChart').getContext('2d');
    new Chart(genderCtx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(genderData),
            datasets: [{
                data: Object.values(genderData),
                backgroundColor: [
                    'rgba(52, 152, 219, 0.8)',
                    'rgba(231, 76, 60, 0.8)',
                    'rgba(155, 89, 182, 0.8)'
                ],
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                }
            }
        }
    });
});

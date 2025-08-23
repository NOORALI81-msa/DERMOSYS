document.addEventListener("DOMContentLoaded", () => {
  const diseaseData = JSON.parse(document.getElementById("diseaseData").textContent);
  const symptomData = JSON.parse(document.getElementById("symptomData").textContent);

  new Chart(document.getElementById('diseaseChart'), {
    type: 'bar',
    data: {
      labels: Object.keys(diseaseData),
      datasets: [{
        label: 'Disease Frequency',
        data: Object.values(diseaseData),
        backgroundColor: '#4e73df'
      }]
    }
  });

  new Chart(document.getElementById('symptomChart'), {
    type: 'bar',
    data: {
      labels: Object.keys(symptomData),
      datasets: [{
        label: 'Symptom Frequency',
        data: Object.values(symptomData),
        backgroundColor: '#1cc88a'
      }]
    }
  });
});

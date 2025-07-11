// dashboard.js

document.addEventListener('DOMContentLoaded', function () {
  const ctx = document.getElementById('grafico').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: window.nombres, // ← lo pasamos desde Flask
      datasets: [{
        label: 'Stock Final',
        data: window.stocks,
        backgroundColor: '#1a73e8'
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true }
      }
    }
  });
});

    // Productivity Bar Chart
    const ctx1 = document.getElementById('productivityChart');
    new Chart(ctx1, {
      type: 'bar',
      data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        datasets: [{
          label: 'Productivity',
          data: [5000, 5500, 4800, 6500, 7200, 8500],
          borderWidth: 1
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } }
      }
    });

    // Emotion Pie Chart
    const ctx2 = document.getElementById('emotionChart');
    new Chart(ctx2, {
      type: 'doughnut',
      data: {
        labels: ['Happy', 'Focused', 'Neutral', 'Angry', 'Sad', 'Tired'],
        datasets: [{
          data: [50, 30, 25, 5, 5, 5],
          backgroundColor: ['#008000', '#19ABB6', '#9ca3af', '#FF0000', '#6F517A', '#FF8800']
        }]
      },
      options: {
        plugins: { legend: { position: 'bottom' } }
      }
    });
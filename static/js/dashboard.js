document.addEventListener('DOMContentLoaded', () => {
    // 1. Fetch statistics from backend API
    fetch('/api/attendance_stats')
        .then(response => response.json())
        .then(data => {
            initWeeklyTrendChart(data.weekly_trend);
            initClassRatesChart(data.class_stats);
            initStatusRatioChart(data.today_ratio);
        })
        .catch(err => {
            console.error('Error fetching statistics:', err);
            // Fallback mock data in case API fails or has empty db
            initWeeklyTrendChart([]);
            initClassRatesChart([]);
            initStatusRatioChart({ present: 0, late: 0, absent: 0 });
        });

    function initWeeklyTrendChart(trendData) {
        const ctx = document.getElementById('weeklyTrendChart');
        if (!ctx) return;

        // If no data, use defaults
        const labels = trendData.length ? trendData.map(d => d.date) : ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        const values = trendData.length ? trendData.map(d => d.rate) : [85, 88, 92, 90, 87, 0, 0];

        // Styling gradient
        const chartCtx = ctx.getContext('2d');
        const gradient = chartCtx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(99, 102, 241, 0.4)');
        gradient.addColorStop(1, 'rgba(99, 102, 241, 0.0)');

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Attendance Rate (%)',
                    data: values,
                    borderColor: '#6366f1',
                    borderWidth: 3,
                    pointBackgroundColor: '#818cf8',
                    pointHoverRadius: 7,
                    fill: true,
                    backgroundColor: gradient,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8
                    }
                },
                scales: {
                    y: {
                        min: 0,
                        max: 100,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: 'var(--text-secondary)' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: 'var(--text-secondary)' }
                    }
                }
            }
        });
    }

    function initClassRatesChart(classStats) {
        const ctx = document.getElementById('classRatesChart');
        if (!ctx) return;

        const labels = classStats.length ? classStats.map(c => c.class_name) : ['Grade 10', 'Grade 11', 'Grade 12', 'CS Dept', 'EE Dept'];
        const values = classStats.length ? classStats.map(c => c.rate) : [90, 85, 95, 88, 82];

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: 'rgba(20, 184, 166, 0.75)',
                    hoverBackgroundColor: '#14b8a6',
                    borderRadius: 8,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        padding: 12,
                        cornerRadius: 8
                    }
                },
                scales: {
                    y: {
                        min: 0,
                        max: 100,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: 'var(--text-secondary)' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: 'var(--text-secondary)' }
                    }
                }
            }
        });
    }

    function initStatusRatioChart(ratioData) {
        const ctx = document.getElementById('statusRatioChart');
        if (!ctx) return;

        // Fallbacks
        const present = ratioData.present || 0;
        const late = ratioData.late || 0;
        const absent = ratioData.absent || 0;

        const isEmpty = (present + late + absent) === 0;
        const dataValues = isEmpty ? [1] : [present, late, absent];
        const dataColors = isEmpty 
            ? ['rgba(148, 163, 184, 0.2)'] 
            : ['#10b981', '#f59e0b', '#ef4444'];
        const labels = isEmpty ? ['No Data Today'] : ['Present', 'Late', 'Absent'];

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dataValues,
                    backgroundColor: dataColors,
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: 'var(--text-secondary)',
                            font: { family: 'Outfit', size: 12 },
                            padding: 15
                        }
                    },
                    tooltip: {
                        enabled: !isEmpty,
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        padding: 12,
                        cornerRadius: 8
                    }
                },
                cutout: '70%'
            }
        });
    }
});

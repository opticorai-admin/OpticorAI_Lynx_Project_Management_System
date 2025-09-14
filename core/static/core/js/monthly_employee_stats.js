(function () {
  try {
    if (!window.ApexCharts) return;

    function parseJSONScript(id) {
      var el = document.getElementById(id);
      if (!el) return null;
      try {
        return JSON.parse(el.textContent || el.innerText || 'null');
      } catch (e) {
        return null;
      }
    }

    function renderStatusBar(containerId, data) {
      var el = document.getElementById(containerId);
      if (!el || !data) return;
      // Always render the standard bar here; monthly trend has its own container now
      var options = {
        chart: { type: 'bar', height: 260, toolbar: { show: false } },
        series: [{ name: data.datasets[0].label || 'Tasks', data: data.datasets[0].data }],
        xaxis: { categories: data.labels },
        plotOptions: { bar: { borderRadius: 6, columnWidth: '45%', distributed: true } },
        dataLabels: { enabled: true },
        // Colors correspond to labels order: Open, Closed, Due
        // Closed should be green, Due should be red
        colors: ['#1abc9c', '#2ecc71', '#e74c3c'],
        tooltip: { theme: 'dark' },
        grid: {
          strokeDashArray: 3,
          xaxis: { lines: { show: true } },
          yaxis: { lines: { show: true } }
        }
      };
      new ApexCharts(el, options).render();
    }

    function renderPriorityDonut(containerId, data) {
      var el = document.getElementById(containerId);
      if (!el || !data) return;
      var options = {
        chart: { type: 'donut', height: 260 },
        series: data.datasets[0].data,
        labels: data.labels,
        colors: data.datasets[0].backgroundColor,
        legend: { position: 'bottom' },
        dataLabels: { enabled: true },
        stroke: { width: 1 },
      };
      new ApexCharts(el, options).render();
    }

    function renderEmployeeStacked(containerId, data) {
      var el = document.getElementById(containerId);
      if (!el || !data) return;
      var series = (data.datasets || []).map(function (ds) {
        return { name: ds.label, data: ds.data };
      });
      var options = {
        chart: { type: 'bar', stacked: true, height: 320, toolbar: { show: false } },
        series: series,
        xaxis: { categories: data.labels },
        plotOptions: {
          bar: {
            borderRadius: 4,
            columnWidth: data.meta && data.meta.xaxis === 'months' ? '35%' : '50%',
            horizontal: false
          }
        },
        legend: { position: 'bottom' },
        dataLabels: { enabled: false },
        // Series order: Assigned, Completed, Open, Closed, Due
        // Ensure Due is red
        colors: ['#95a5a6', '#4BC0C0', '#36A2EB', '#2ecc71', '#e74c3c'],
        grid: {
          strokeDashArray: 3,
          xaxis: { lines: { show: true } },
          yaxis: { lines: { show: true } }
        },
        tooltip: { theme: 'dark' }
      };
      new ApexCharts(el, options).render();
    }

    function renderMonthlyTrend(containerId, data) {
      var el = document.getElementById(containerId);
      if (!el || !data) return;
      var series = (data.datasets || []).map(function (ds) {
        return { name: ds.label, data: ds.data };
      });
      var options = {
        chart: { type: 'line', height: 320, toolbar: { show: false } },
        series: series,
        xaxis: {
          categories: data.labels,
          tickPlacement: 'on',
          axisBorder: { show: true },
          axisTicks: { show: true },
          crosshairs: { show: true }
        },
        dataLabels: { enabled: false },
        stroke: { width: 2, curve: 'smooth' },
        legend: { position: 'bottom' },
        tooltip: { theme: 'dark' },
        grid: {
          strokeDashArray: 3,
          xaxis: { lines: { show: true } },
          yaxis: { lines: { show: true } }
        },
      };
      new ApexCharts(el, options).render();
    }

    // Parse JSON payloads from template
    var statusData = parseJSONScript('monthly-status-data');
    var priorityData = parseJSONScript('priority-data');
    var employeeData = parseJSONScript('employee-status-data');
    var trendData = parseJSONScript('monthly-trend-data');

    renderStatusBar('apex-monthlyStatus', statusData);
    renderPriorityDonut('apex-priority', priorityData);
    renderEmployeeStacked('apex-employeeStatus', employeeData);
    renderMonthlyTrend('apex-monthlyTrend', trendData);
  } catch (e) {
    // no-op
  }
})();



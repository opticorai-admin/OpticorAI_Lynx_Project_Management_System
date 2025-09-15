/* Monthly Employee Stats charts (ApexCharts) — improved readability and styling */
(function () {
  try {
    if (!window.ApexCharts) return;

    function parseJSONScript(id) {
      var el = document.getElementById(id);
      if (!el) return null;
      try { return JSON.parse(el.textContent || el.innerText || 'null'); } catch (e) { return null; }
    }

    function baseGrid() {
      return {
        strokeDashArray: 3,
        xaxis: { lines: { show: true } },
        yaxis: { lines: { show: true } }
      };
    }

    function baseLegend() {
      return { position: 'bottom', markers: { radius: 2 } };
    }

    function baseTooltip() { return { theme: 'dark' }; }

    function renderStatusBar(containerId, data) {
      var el = document.getElementById(containerId);
      if (!el || !data || !data.datasets || !data.datasets.length) return;
      var options = {
        chart: { type: 'bar', height: 280, toolbar: { show: false } },
        title: { text: 'Monthly Task Status', align: 'center' },
        series: [{ name: data.datasets[0].label || 'Tasks', data: data.datasets[0].data }],
        xaxis: { categories: data.labels, labels: { style: { fontSize: '12px' } }, title: { text: 'Status' } },
        yaxis: { title: { text: 'Number of Tasks' } },
        plotOptions: { bar: { borderRadius: 6, columnWidth: '45%', distributed: true } },
        dataLabels: { enabled: true, style: { fontSize: '12px' } },
        colors: ['#ffc107', '#198754', '#dc3545'],
        tooltip: baseTooltip(),
        grid: baseGrid(),
        legend: baseLegend()
      };
      new ApexCharts(el, options).render();
    }

    function renderPriorityDonut(containerId, data) {
      var el = document.getElementById(containerId);
      if (!el || !data || !data.datasets || !data.datasets.length) return;
      var options = {
        chart: { type: 'donut', height: 280 },
        title: { text: 'Task Priority Distribution', align: 'center' },
        series: data.datasets[0].data,
        labels: data.labels,
        colors: data.datasets[0].backgroundColor,
        legend: baseLegend(),
        dataLabels: { enabled: true, style: { fontSize: '12px' } },
        stroke: { width: 1 },
      };
      new ApexCharts(el, options).render();
    }

    function renderEmployeeStacked(containerId, data) {
      var el = document.getElementById(containerId);
      if (!el || !data) return;
      var series = (data.datasets || []).map(function (ds) { return { name: ds.label, data: ds.data }; });
      var options = {
        chart: { type: 'bar', stacked: true, height: 340, toolbar: { show: false } },
        title: { text: 'Tasks by Employee', align: 'center' },
        series: series,
        xaxis: { categories: data.labels, labels: { rotateAlways: false, trim: true, style: { fontSize: '12px' } }, title: { text: 'Employees' } },
        yaxis: { title: { text: 'Number of Tasks' } },
        plotOptions: { bar: { borderRadius: 6, columnWidth: (data.meta && data.meta.xaxis === 'months') ? '35%' : '50%' } },
        legend: baseLegend(),
        dataLabels: { enabled: false },
        colors: ['#6c757d', '#ffc107', '#198754', '#dc3545'],
        grid: baseGrid(),
        tooltip: baseTooltip()
      };
      new ApexCharts(el, options).render();
    }

    function renderMonthlyTrend(containerId, data) {
      var el = document.getElementById(containerId);
      if (!el || !data) return;
      var series = (data.datasets || []).map(function (ds) { return { name: ds.label, data: ds.data }; });
      var options = {
        chart: { type: 'line', height: 340, toolbar: { show: false } },
        title: { text: 'Monthly Task Creation Trend', align: 'center' },
        series: series,
        xaxis: { categories: data.labels, tickPlacement: 'on', labels: { style: { fontSize: '12px' } }, title: { text: 'Month' } },
        yaxis: { title: { text: 'Number of Tasks' } },
        dataLabels: { enabled: false },
        stroke: { width: 2, curve: 'smooth' },
        legend: baseLegend(),
        tooltip: baseTooltip(),
        grid: baseGrid()
      };
      new ApexCharts(el, options).render();
    }

    var statusData = parseJSONScript('monthly-status-data');
    var priorityData = parseJSONScript('priority-data');
    var employeeData = parseJSONScript('employee-status-data');
    var trendData = parseJSONScript('monthly-trend-data');

    renderStatusBar('apex-monthlyStatus', statusData);
    renderPriorityDonut('apex-priority', priorityData);
    renderEmployeeStacked('apex-employeeStatus', employeeData);
    renderMonthlyTrend('apex-monthlyTrend', trendData);
  } catch (e) { /* no-op */ }
})();



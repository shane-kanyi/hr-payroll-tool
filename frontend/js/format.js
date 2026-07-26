const Format = (() => {
  function money(value) {
    if (value === null || value === undefined) return "—";
    const num = Number(value);
    return `$${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  function date(value) {
    if (!value) return "—";
    return value.slice(0, 10);
  }

  function dateTime(value) {
    if (!value) return "—";
    return new Date(value).toLocaleString();
  }

  function days(value) {
    if (value === null || value === undefined) return "—";
    const num = Number(value);
    return num === 1 ? "1 day" : `${num} days`;
  }

  const MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];

  function monthLabel(year, month) {
    return `${MONTH_NAMES[month - 1]} ${year}`;
  }

  function statusBadgeClass(status) {
    return `badge badge-${status}`;
  }

  function titleCase(value) {
    if (!value) return "";
    return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  return { money, date, dateTime, days, monthLabel, statusBadgeClass, titleCase, MONTH_NAMES };
})();

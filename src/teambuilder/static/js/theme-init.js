if (
	(localStorage.getItem("darkTheme") ||
		"" +
			window.matchMedia("(prefers-color-scheme: dark)").matches) ===
	"false"
) {
	document.getElementById("dark-theme-styles").disabled = true;
}

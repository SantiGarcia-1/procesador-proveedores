const API_BASE_URL = "";

const form = document.querySelector("#upload-form");
const supplierInput = document.querySelector("#proveedor");
const fileInput = document.querySelector("#archivo");
const dropZone = document.querySelector("#drop-zone");
const fileLabel = document.querySelector("#file-label");
const statusMessage = document.querySelector("#status-message");
const processButton = document.querySelector("#process-button");
const buttonLabel = document.querySelector("#button-label");
const spinner = document.querySelector("#spinner");
const providersList = document.querySelector("#proveedores-list");
const resultsBody = document.querySelector("#results-body");
const resultsCaption = document.querySelector("#results-caption");
const emptyState = document.querySelector("#empty-state");
const tableContainer = document.querySelector("#table-container");
const downloadButton = document.querySelector("#download-button");
const themeToggle = document.querySelector("#theme-toggle");
const themeLabel = document.querySelector("#theme-label");
const darkThemeIcon = document.querySelector("#theme-icon-dark");
const lightThemeIcon = document.querySelector("#theme-icon-light");

function actualizarControlTema() {
  const modoOscuro = document.documentElement.classList.contains("dark");
  themeToggle.setAttribute("aria-pressed", String(modoOscuro));
  themeToggle.setAttribute("aria-label", `Activar modo ${modoOscuro ? "claro" : "oscuro"}`);
  themeLabel.textContent = `Modo ${modoOscuro ? "claro" : "oscuro"}`;
  darkThemeIcon.classList.toggle("hidden", modoOscuro);
  lightThemeIcon.classList.toggle("hidden", !modoOscuro);
}

actualizarControlTema();

themeToggle.addEventListener("click", () => {
  const modoOscuro = document.documentElement.classList.toggle("dark");
  actualizarControlTema();
  localStorage.setItem("theme", modoOscuro ? "dark" : "light");
});

function mostrarEstado(mensaje, tipo = "info") {
  const estilos = {
    info: "bg-blue-50 text-blue-800 dark:bg-blue-950 dark:text-blue-200",
    error: "bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-200",
    success: "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  };
  statusMessage.className = `mt-4 rounded-lg px-4 py-3 text-sm ${estilos[tipo]}`;
  statusMessage.textContent = mensaje;
}

function seleccionarArchivo(archivo) {
  if (!archivo) return;
  if (archivo.type !== "application/pdf" && !archivo.name.toLowerCase().endsWith(".pdf")) {
    fileInput.value = "";
    fileLabel.textContent = "Arrastrá tu PDF acá";
    mostrarEstado("Seleccioná un archivo PDF para continuar.", "error");
    return;
  }
  fileInput.files = crearListaArchivos(archivo);
  fileLabel.textContent = archivo.name;
  statusMessage.classList.add("hidden");
}

function crearListaArchivos(archivo) {
  const transferencia = new DataTransfer();
  transferencia.items.add(archivo);
  return transferencia.files;
}

function agregarCelda(fila, contenido, clases = "") {
  const celda = document.createElement("td");
  celda.className = `px-2.5 py-2 ${clases}`;
  celda.textContent = contenido;
  celda.title = contenido;
  fila.append(celda);
}

function formatearPrecio(precio, moneda) {
  if (precio === null || precio === undefined) return "—";
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: moneda || "ARS",
    maximumFractionDigits: 2,
  }).format(precio).replace(/\u00a0/g, " ");
}

function limpiarNombreArchivo(valor) {
  const sinAcentos = valor.normalize("NFKD").replace(/[\u0300-\u036f]/g, "");
  return sinAcentos.replace(/[^A-Za-z0-9_-]+/g, "_").replace(/^[_-]+|[_-]+$/g, "") || "proveedor";
}

function crearNombreArchivo(proveedor, fecha) {
  return `${limpiarNombreArchivo(proveedor)}_${limpiarNombreArchivo(fecha || "sin_fecha")}.xlsx`;
}

function obtenerNombreArchivo(contentDisposition) {
  const utf8Match = /filename\*=UTF-8''([^;]+)/i.exec(contentDisposition);
  if (utf8Match) return decodeURIComponent(utf8Match[1]);
  const nombreMatch = /filename="?([^";]+)"?/i.exec(contentDisposition);
  return nombreMatch ? nombreMatch[1] : null;
}

function renderizarItems(items, proveedor, fecha) {
  resultsBody.replaceChildren();
  for (const item of items) {
    const fila = document.createElement("tr");
    const variacion = item.porcentaje_variacion;
    if (variacion !== null && variacion > 10) {
      fila.className = "bg-red-50 dark:bg-red-950";
    }

    agregarCelda(fila, item.codigo_sku || "—", "max-w-0 truncate whitespace-nowrap text-slate-500 dark:text-slate-400");
    agregarCelda(fila, item.descripcion, "max-w-[200px] truncate font-medium text-slate-800 dark:text-slate-100");
    agregarCelda(fila, formatearPrecio(item.precio_anterior, item.moneda), "text-right text-slate-600 dark:text-slate-400");
    agregarCelda(fila, formatearPrecio(item.precio_unitario, item.moneda), "text-right font-medium text-slate-900 dark:text-slate-100");
    const variacionTexto =
      variacion === null || variacion === undefined
        ? "Sin historial"
        : `${variacion > 0 ? "+" : ""}${variacion.toFixed(2)}%`;
    agregarCelda(
      fila,
      variacionTexto,
      `whitespace-nowrap text-right font-semibold ${variacion > 10 ? "text-red-700 dark:text-red-300" : variacion < 0 ? "text-emerald-700 dark:text-emerald-300" : "text-slate-600 dark:text-slate-400"}`,
    );
    resultsBody.append(fila);
  }

  const detalleFecha = fecha ? ` · Documento del ${fecha}` : "";
  resultsCaption.textContent = `${items.length} productos · ${proveedor}${detalleFecha}`;
  emptyState.classList.add("hidden");
  tableContainer.classList.remove("hidden");
}

async function cargarProveedores() {
  try {
    const respuesta = await fetch(`${API_BASE_URL}/api/proveedores`);
    if (!respuesta.ok) throw new Error("No se pudo cargar la lista de proveedores.");
    const datos = await respuesta.json();
    providersList.replaceChildren();
    for (const nombre of datos.proveedores) {
      const opcion = document.createElement("option");
      opcion.value = nombre;
      providersList.append(opcion);
    }
  } catch (error) {
    mostrarEstado(error.message, "error");
  }
}

downloadButton.addEventListener("click", async (evento) => {
  evento.preventDefault();
  try {
    const respuesta = await fetch(downloadButton.href);
    if (!respuesta.ok) {
      throw new Error(`No se pudo descargar el Excel (HTTP ${respuesta.status}).`);
    }

    const blob = await respuesta.blob();
    const contentDisposition = respuesta.headers.get("Content-Disposition") || "";
    const nombreArchivo =
      obtenerNombreArchivo(contentDisposition) ||
      downloadButton.dataset.filename ||
      "comparacion.xlsx";
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = nombreArchivo;
    enlace.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {
    mostrarEstado(error.message || "No se pudo descargar el archivo Excel.", "error");
  }
});

fileInput.addEventListener("change", () => seleccionarArchivo(fileInput.files[0]));

for (const evento of ["dragenter", "dragover"]) {
  dropZone.addEventListener(evento, (e) => {
    e.preventDefault();
    dropZone.classList.add("border-blue-500", "bg-blue-50");
  });
}

for (const evento of ["dragleave", "drop"]) {
  dropZone.addEventListener(evento, (e) => {
    e.preventDefault();
    dropZone.classList.remove("border-blue-500", "bg-blue-50");
  });
}

dropZone.addEventListener("drop", (e) => seleccionarArchivo(e.dataTransfer.files[0]));

form.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const archivo = fileInput.files[0];
  if (!archivo) {
    mostrarEstado("Seleccioná un PDF antes de procesar.", "error");
    return;
  }

  const datos = new FormData();
  datos.append("proveedor", supplierInput.value.trim());
  datos.append("file", archivo);
  processButton.disabled = true;
  spinner.classList.remove("hidden");
  buttonLabel.textContent = "Analizando documento…";
  mostrarEstado("Extrayendo productos y comparando precios. Esto puede tardar un momento.", "info");

  try {
    const respuesta = await fetch(`${API_BASE_URL}/api/procesar`, { method: "POST", body: datos });
    const resultado = await respuesta.json();
    if (!respuesta.ok) {
      throw new Error(resultado.detail || "No se pudo procesar el documento.");
    }

    renderizarItems(resultado.items, resultado.proveedor, resultado.fecha_documento);
    downloadButton.href = `${API_BASE_URL}/api/descargar-excel/${encodeURIComponent(resultado.lote_id)}`;
    downloadButton.dataset.filename = crearNombreArchivo(
      resultado.proveedor,
      resultado.fecha_documento,
    );
    downloadButton.classList.remove("hidden");
    downloadButton.classList.add("inline-flex");
    mostrarEstado("La lista se procesó correctamente.", "success");
    await cargarProveedores();
  } catch (error) {
    mostrarEstado(error.message || "Ocurrió un error al procesar el archivo.", "error");
  } finally {
    processButton.disabled = false;
    spinner.classList.add("hidden");
    buttonLabel.textContent = "Procesar lista";
  }
});

cargarProveedores();

/**
 * Aplicación Frontend - Seguimiento Legislativo
 * Gestiona carga de datos, filtros, paginación
 */

let currentPage = 1;
let totalPages = 1;
let currentFilters = {};
let currentCamara = null;

/**
 * Cargar datos y estadísticas para una cámara
 */
async function cargarDatos(camara) {
    currentCamara = camara;
    currentPage = 1;
    
    // Cargar estadísticas
    try {
        const response = await fetch(`/api/stats?camara=${encodeURIComponent(camara)}`);
        const stats = await response.json();
        mostrarEstadisticas(stats);
    } catch (error) {
        console.error('Error cargando estadísticas:', error);
    }
    
    // Cargar iniciativas
    cargarIniciativas();
}

/**
 * Mostrar estadísticas en la página
 */
function mostrarEstadisticas(stats) {
    const statsHtml = `
        <div class="col-md-6 col-lg-3">
            <div class="card bg-primary text-white">
                <div class="card-body text-center">
                    <div class="stat-number">${stats.total || 0}</div>
                    <p class="card-text small">Total Iniciativas</p>
                </div>
            </div>
        </div>
        <div class="col-md-6 col-lg-3">
            <div class="card bg-success text-white">
                <div class="card-body text-center">
                    <div class="stat-number">${stats.estados?.aprobada || 0}</div>
                    <p class="card-text small">Aprobadas</p>
                </div>
            </div>
        </div>
        <div class="col-md-6 col-lg-3">
            <div class="card bg-danger text-white">
                <div class="card-body text-center">
                    <div class="stat-number">${stats.estados?.rechazada || 0}</div>
                    <p class="card-text small">Rechazadas</p>
                </div>
            </div>
        </div>
        <div class="col-md-6 col-lg-3">
            <div class="card bg-warning text-dark">
                <div class="card-body text-center">
                    <div class="stat-number">${stats.estados?.pendiente || 0}</div>
                    <p class="card-text small">Pendientes</p>
                </div>
            </div>
        </div>
    `;
    
    const statsRow = document.getElementById('stats-row');
    if (statsRow) {
        statsRow.innerHTML = statsHtml;
    }
}

/**
 * Cargar iniciativas con filtros
 */
async function cargarIniciativas() {
    const params = new URLSearchParams({
        camara: currentCamara,
        pagina: currentPage,
        por_pagina: 10
    });
    
    if (currentFilters.estado) {
        params.append('estado', currentFilters.estado);
    }
    if (currentFilters.tipo) {
        params.append('tipo', currentFilters.tipo);
    }
    if (currentFilters.q) {
        params.append('q', currentFilters.q);
    }
    
    try {
        const response = await fetch(`/api/iniciativas?${params}`);
        const data = await response.json();
        
        mostrarIniciativas(data.datos);
        actualizarPaginacion(data);
    } catch (error) {
        console.error('Error cargando iniciativas:', error);
        document.getElementById('iniciativas-container').innerHTML = 
            '<div class="alert alert-danger">Error cargando iniciativas</div>';
    }
}

/**
 * Mostrar lista de iniciativas
 */
function mostrarIniciativas(iniciativas) {
    const container = document.getElementById('iniciativas-container');
    
    if (!iniciativas || iniciativas.length === 0) {
        container.innerHTML = '<div class="alert alert-info">No se encontraron iniciativas</div>';
        return;
    }
    
    const html = iniciativas.map(ini => {
        // Generar HTML para posiciones de partidos
        let posicionesHtml = '';
        if (ini.posicion_grupos && typeof ini.posicion_grupos === 'object' && Object.keys(ini.posicion_grupos).length > 0) {
            const posiciones = Object.entries(ini.posicion_grupos).map(([grupo, posicion]) => {
                const posicionLower = posicion?.toLowerCase() || 'desconocido';
                const clasePosicion = posicionLower.includes('favor') ? 'favor' : 
                                     posicionLower.includes('contra') ? 'contra' :
                                     posicionLower.includes('abstención') ? 'abstencion' : 'desconocido';
                return `
                    <div class="posicion-grupo">
                        <span class="posicion-grupo-nombre">${escaparHtml(grupo)}</span>
                        <span class="posicion-grupo-voto ${clasePosicion}">${escaparHtml(posicion || 'Desconocido')}</span>
                    </div>
                `;
            }).join('');
            
            posicionesHtml = `
                <div class="posiciones-container">
                    <div class="posiciones-titulo">
                        <i class="fas fa-chart-pie"></i> Posiciones de Partidos
                    </div>
                    <div class="posiciones-grid">
                        ${posiciones}
                    </div>
                </div>
            `;
        }
        
        return `
        <div class="card iniciativa-card ${ini.estado || 'pendiente'}">
            <div class="card-body">
                <div class="row mb-2">
                    <div class="col-md-9">
                        <h5 class="iniciativa-titulo">${escaparHtml(ini.titulo)}</h5>
                    </div>
                    <div class="col-md-3 text-end">
                        <span class="estado-badge ${ini.estado || 'pendiente'}">
                            ${(ini.estado || 'pendiente').charAt(0).toUpperCase() + (ini.estado || 'pendiente').slice(1)}
                        </span>
                    </div>
                </div>
                
                <p class="iniciativa-resumen">${escaparHtml(ini.resumen || '')}</p>
                
                <div class="iniciativa-meta mb-2">
                    <div class="iniciativa-meta-item">
                        <i class="fas fa-file-alt"></i>
                        <span>${escaparHtml(ini.tipo || 'Sin tipo')}</span>
                    </div>
                    ${ini.grupo_autor ? `
                        <div class="iniciativa-meta-item">
                            <i class="fas fa-users"></i>
                            <span>${escaparHtml(ini.grupo_autor)}</span>
                        </div>
                    ` : ''}
                    ${ini.fecha_presentacion ? `
                        <div class="iniciativa-meta-item">
                            <i class="fas fa-calendar-alt"></i>
                            <span>${formatarFecha(ini.fecha_presentacion)}</span>
                        </div>
                    ` : ''}
                </div>
                
                ${ini.tematicas && ini.tematicas.length > 0 ? `
                    <div class="mt-2">
                        ${ini.tematicas.map(tema => 
                            `<span class="tema-badge">${escaparHtml(tema)}</span>`
                        ).join('')}
                    </div>
                ` : ''}
                
                ${posicionesHtml}
                
                <div class="mt-3">
                    <a href="${escaparHtml(ini.url)}" target="_blank" class="btn btn-sm btn-outline-primary">
                        <i class="fas fa-external-link-alt"></i> Ver en oficial
                    </a>
                </div>
            </div>
        </div>
    `;
    }).join('');
    
    container.innerHTML = html;
}

/**
 * Actualizar controles de paginación
 */
function actualizarPaginacion(data) {
    totalPages = data.paginas || 1;
    const paginationNav = document.getElementById('pagination-nav');
    
    if (totalPages <= 1) {
        if (paginationNav) paginationNav.style.display = 'none';
        return;
    }
    
    if (paginationNav) {
        paginationNav.style.display = 'block';
    }
    
    const currentPageSpan = document.getElementById('current-page');
    if (currentPageSpan) {
        currentPageSpan.textContent = currentPage;
    }
    
    // Prev
    const prevBtn = document.getElementById('prev-btn');
    if (prevBtn) {
        if (currentPage > 1) {
            prevBtn.style.display = 'block';
            prevBtn.querySelector('a').onclick = (e) => {
                e.preventDefault();
                currentPage--;
                cargarIniciativas();
                window.scrollTo(0, 0);
            };
        } else {
            prevBtn.style.display = 'none';
        }
    }
    
    // Next
    const nextBtn = document.getElementById('next-btn');
    if (nextBtn) {
        if (currentPage < totalPages) {
            nextBtn.style.display = 'block';
            nextBtn.querySelector('a').onclick = (e) => {
                e.preventDefault();
                currentPage++;
                cargarIniciativas();
                window.scrollTo(0, 0);
            };
        } else {
            nextBtn.style.display = 'none';
        }
    }
}

/**
 * Aplicar filtros
 */
function aplicarFiltros() {
    const searchInput = document.getElementById('search-input');
    const estadoFilter = document.getElementById('estado-filter');
    const tipoFilter = document.getElementById('tipo-filter');
    
    currentFilters = {};
    if (searchInput?.value) currentFilters.q = searchInput.value;
    if (estadoFilter?.value) currentFilters.estado = estadoFilter.value;
    if (tipoFilter?.value) currentFilters.tipo = tipoFilter.value;
    
    currentPage = 1;
    cargarIniciativas();
}

/**
 * Formatear fecha YYYY-MM-DD a formato legible
 */
function formatarFecha(fecha) {
    if (!fecha) return '';
    try {
        const date = new Date(fecha);
        return date.toLocaleDateString('es-ES', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });
    } catch {
        return fecha;
    }
}

/**
 * Escapar HTML para evitar XSS
 */
function escaparHtml(texto) {
    if (!texto) return '';
    const div = document.createElement('div');
    div.textContent = texto;
    return div.innerHTML;
}

/**
 * Cargar estadísticas globales en inicio
 */
async function cargarEstadisticas() {
    try {
        const congresoRes = await fetch('/api/stats?camara=Congreso%20de%20Diputados');
        const congresoStats = await congresoRes.json();
        
        const andaluciaRes = await fetch('/api/stats?camara=Parlamento%20de%20Andaluc%C3%ADa');
        const andaluciaStats = await andaluciaRes.json();
        
        const statsContainer = document.getElementById('stats-container');
        if (statsContainer) {
            statsContainer.innerHTML = `
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-label">Congreso Total</div>
                        <div class="stat-number">${congresoStats.total || 0}</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-label">Congreso Aprobadas</div>
                        <div class="stat-number" style="color: var(--success);">${congresoStats.estados?.aprobada || 0}</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-label">Andalucía Total</div>
                        <div class="stat-number">${andaluciaStats.total || 0}</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-label">Andalucía Aprobadas</div>
                        <div class="stat-number" style="color: var(--success);">${andaluciaStats.estados?.aprobada || 0}</div>
                    </div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error cargando estadísticas globales:', error);
    }
}

/**
 * Event listeners al cargar página
 */
document.addEventListener('DOMContentLoaded', function() {
    // Filtros
    const applyFilterBtn = document.getElementById('apply-filters');
    if (applyFilterBtn) {
        applyFilterBtn.addEventListener('click', aplicarFiltros);
    }
    
    // Enter en búsqueda
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                aplicarFiltros();
            }
        });
    }
});

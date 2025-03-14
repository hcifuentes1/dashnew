"""
Utilidades para generación y exportación de reportes.

Este módulo contiene funciones para generar informes en diferentes formatos
(PDF, CSV, etc.) basados en los datos del sistema de monitoreo.
"""
import os
import sys
import io
import base64
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Importar módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import MONITORING_PARAMS, DATA_DIR, REPORTS_DIR

# Asegurar que el directorio de reportes exista
os.makedirs(REPORTS_DIR, exist_ok=True)

def generate_pdf_report(report_type, machine_id, start_date, end_date, health_data=None, alerts_data=None, maintenance_data=None):
    """
    Genera un informe en formato PDF.
    
    Args:
        report_type: Tipo de reporte ('health', 'alerts', 'maintenance', 'performance')
        machine_id: ID de la máquina o 'all' para todas
        start_date: Fecha de inicio del período
        end_date: Fecha de fin del período
        health_data: Datos de salud (opcional)
        alerts_data: Datos de alertas (opcional)
        maintenance_data: Datos de mantenimiento (opcional)
        
    Returns:
        bytes: Contenido del PDF generado
    """
    # Preparar buffer para almacenar PDF
    buffer = io.BytesIO()
    
    # Crear documento
    doc = SimpleDocTemplate(buffer, pagesize=letter, title="Reporte de Monitoreo")
    
    # Estilos
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='Title',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=20
    ))
    styles.add(ParagraphStyle(
        name='Subtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        name='Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER
    ))
    
    # Contenido del PDF
    elements = []
    
    # Título según tipo de reporte
    if report_type == 'health':
        title = "Reporte de Estado de Salud"
    elif report_type == 'alerts':
        title = "Reporte de Alertas"
    elif report_type == 'maintenance':
        title = "Reporte de Mantenimiento"
    elif report_type == 'performance':
        title = "Análisis de Rendimiento"
    else:
        title = "Reporte de Monitoreo"
    
    elements.append(Paragraph(title, styles['Title']))
    
    # Información general del reporte
    elements.append(Paragraph("Información General", styles['Subtitle']))
    
    # Tabla de información
    info_data = [
        ["Período", f"{start_date} a {end_date}"],
        ["Máquina(s)", "Todas" if machine_id == 'all' else MONITORING_PARAMS.get(machine_id, {}).get('name', machine_id)],
        ["Fecha de generación", datetime.now().strftime("%d/%m/%Y %H:%M:%S")],
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Contenido específico según el tipo de reporte
    if report_type == 'health':
        _add_health_report_content(elements, styles, machine_id, start_date, end_date, health_data)
    elif report_type == 'alerts':
        _add_alerts_report_content(elements, styles, machine_id, start_date, end_date, alerts_data)
    elif report_type == 'maintenance':
        _add_maintenance_report_content(elements, styles, machine_id, start_date, end_date, maintenance_data)
    elif report_type == 'performance':
        _add_performance_report_content(elements, styles, machine_id, start_date, end_date)
    
    # Construir PDF
    doc.build(elements, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    
    # Obtener contenido
    buffer.seek(0)
    return buffer.getvalue()

def _add_page_number(canvas, doc):
    """Agrega número de página al pie de página."""
    page_num = canvas.getPageNumber()
    text = f"Página {page_num}"
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(letter[0] - 30, 30, text)
    
    # Agregar logo o cabecera
    canvas.drawString(30, 30, "Metro de Santiago - Monitoreo de Máquinas de Cambio")

def _add_health_report_content(elements, styles, machine_id, start_date, end_date, health_data=None):
    """Agrega contenido específico para el reporte de salud."""
    elements.append(Paragraph("Estado de Salud", styles['Subtitle']))
    
    # Si no se proporcionaron datos, agregar mensaje
    if not health_data:
        elements.append(Paragraph("No hay datos de salud disponibles para el período seleccionado.", styles['Normal']))
        return
    
    # Proceso de datos de salud
    health_summary = []
    
    # Encabezados de la tabla
    health_summary.append([
        "Máquina", "Salud General", "Salud Eléctrica", "Salud Mecánica", "Salud Control"
    ])
    
    # Datos por máquina
    for machine, data in health_data.items():
        health_summary.append([
            MONITORING_PARAMS.get(machine, {}).get('name', machine),
            f"{data['overall_health']:.1f}%",
            f"{data['electrical_health']:.1f}%",
            f"{data['mechanical_health']:.1f}%",
            f"{data['control_health']:.1f}%",
        ])
    
    # Crear tabla
    health_table = Table(health_summary)
    health_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(health_table)
    elements.append(Spacer(1, 15))
    
    # Agregar gráfico si hay datos suficientes
    if len(health_data) > 0:
        # Crear gráfico con matplotlib
        plt.figure(figsize=(7, 4))
        
        for machine, data in health_data.items():
            machine_name = MONITORING_PARAMS.get(machine, {}).get('name', machine)
            plt.plot(data['timestamps'], data['overall_health'], label=machine_name)
        
        plt.axhline(y=70, color='orange', linestyle='--', alpha=0.7)
        plt.axhline(y=40, color='red', linestyle='--', alpha=0.7)
        
        plt.title('Tendencia de Salud General')
        plt.xlabel('Fecha')
        plt.ylabel('Salud (%)')
        plt.ylim(0, 100)
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        
        # Guardar gráfico en un buffer
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png')
        img_buffer.seek(0)
        plt.close()
        
        # Agregar imagen al PDF
        img = Image(img_buffer, width=6.5*inch, height=3.5*inch)
        elements.append(img)
    
    elements.append(Spacer(1, 15))
    
    # Agregar conclusiones y recomendaciones
    elements.append(Paragraph("Conclusiones y Recomendaciones", styles['Subtitle']))
    
    # Determinar estado general
    overall_scores = [data['overall_health'] for data in health_data.values()]
    avg_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0
    
    if avg_score >= 85:
        status = "NORMAL"
        elements.append(Paragraph("El estado general de las máquinas es NORMAL. No se requieren acciones inmediatas.", styles['Normal']))
    elif avg_score >= 60:
        status = "REQUIERE ATENCIÓN"
        elements.append(Paragraph("El estado general de las máquinas REQUIERE ATENCIÓN. Se recomienda programar mantenimiento preventivo en las próximas semanas.", styles['Normal']))
    else:
        status = "CRÍTICO"
        elements.append(Paragraph("El estado general de las máquinas es CRÍTICO. Se recomienda programar mantenimiento correctivo lo antes posible.", styles['Normal']))
    
    elements.append(Spacer(1, 10))
    
    # Recomendaciones específicas
    recommendations = [
        "Verificar sistemas de alimentación eléctrica en máquinas con salud eléctrica baja.",
        "Revisar componentes mecánicos en máquinas con salud mecánica inferior al 70%.",
        "Programar inspecciones visuales semanales para máquinas en estado de advertencia.",
        "Verificar corrientes de fase en máquinas con alertas de desequilibrio.",
    ]
    
    for rec in recommendations:
        elements.append(Paragraph(f"• {rec}", styles['Normal']))

def _add_alerts_report_content(elements, styles, machine_id, start_date, end_date, alerts_data=None):
    """Agrega contenido específico para el reporte de alertas."""
    elements.append(Paragraph("Resumen de Alertas", styles['Subtitle']))
    
    # Si no se proporcionaron datos, agregar mensaje
    if not alerts_data or len(alerts_data) == 0:
        elements.append(Paragraph("No hay alertas registradas en el período seleccionado.", styles['Normal']))
        return
    
    # Estadísticas de alertas
    critical_count = len([a for a in alerts_data if a['severity'] == 'critical'])
    warning_count = len([a for a in alerts_data if a['severity'] == 'warning'])
    
    stats_data = [
        ["Total de alertas", str(len(alerts_data))],
        ["Alertas críticas", str(critical_count)],
        ["Alertas de advertencia", str(warning_count)],
    ]
    
    stats_table = Table(stats_data, colWidths=[2*inch, 1*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(stats_table)
    elements.append(Spacer(1, 15))
    
    # Gráfico de alertas por máquina
    if len(alerts_data) > 0:
        # Contar alertas por máquina
        machine_counts = {}
        for alert in alerts_data:
            machine = alert['machine_id']
            machine_name = MONITORING_PARAMS.get(machine, {}).get('name', machine)
            if machine_name not in machine_counts:
                machine_counts[machine_name] = {'critical': 0, 'warning': 0}
            
            if alert['severity'] == 'critical':
                machine_counts[machine_name]['critical'] += 1
            else:
                machine_counts[machine_name]['warning'] += 1
        
        # Crear gráfico con matplotlib
        plt.figure(figsize=(7, 4))
        
        machines = list(machine_counts.keys())
        critical_values = [machine_counts[m]['critical'] for m in machines]
        warning_values = [machine_counts[m]['warning'] for m in machines]
        
        x = np.arange(len(machines))
        width = 0.35
        
        plt.bar(x - width/2, critical_values, width, label='Críticas', color='red')
        plt.bar(x + width/2, warning_values, width, label='Advertencias', color='orange')
        
        plt.xlabel('Máquina')
        plt.ylabel('Número de Alertas')
        plt.title('Alertas por Máquina')
        plt.xticks(x, machines, rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()
        
        # Guardar gráfico en un buffer
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png')
        img_buffer.seek(0)
        plt.close()
        
        # Agregar imagen al PDF
        img = Image(img_buffer, width=6.5*inch, height=3.5*inch)
        elements.append(img)
        elements.append(Spacer(1, 15))
    
    # Lista de alertas
    elements.append(Paragraph("Detalle de Alertas", styles['Subtitle']))
    
    # Preparar datos para la tabla
    alert_details = [["Fecha", "Máquina", "Tipo", "Valor", "Severidad"]]
    
    for alert in alerts_data[:20]:  # Limitar a 20 alertas para no hacer el PDF muy largo
        machine_name = MONITORING_PARAMS.get(alert['machine_id'], {}).get('name', alert['machine_id'])
        
        alert_details.append([
            alert.get('timestamp', '').strftime("%d/%m/%Y %H:%M:%S") if isinstance(alert.get('timestamp', ''), datetime) else alert.get('timestamp', ''),
            machine_name,
            alert.get('alert_type', ''),
            f"{alert.get('value', 0):.2f}" if isinstance(alert.get('value', 0), (int, float)) else str(alert.get('value', '')),
            alert.get('severity', '').upper(),
        ])
    
    # Crear tabla
    alert_table = Table(alert_details)
    alert_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
        # Colorear según severidad
        ('TEXTCOLOR', (4, 1), (4, -1), colors.red, lambda x: x.get(4, "") == "CRITICAL"),
        ('TEXTCOLOR', (4, 1), (4, -1), colors.orange, lambda x: x.get(4, "") == "WARNING"),
    ]))
    
    elements.append(alert_table)

def _add_maintenance_report_content(elements, styles, machine_id, start_date, end_date, maintenance_data=None):
    """Agrega contenido específico para el reporte de mantenimiento."""
    elements.append(Paragraph("Historial de Mantenimiento", styles['Subtitle']))
    
    # Si no se proporcionaron datos, agregar mensaje
    if not maintenance_data or len(maintenance_data) == 0:
        elements.append(Paragraph("No hay registros de mantenimiento en el período seleccionado.", styles['Normal']))
        return
    
    # Estadísticas de mantenimiento
    preventive_count = len([m for m in maintenance_data if m['maintenance_type'] == 'preventive'])
    corrective_count = len([m for m in maintenance_data if m['maintenance_type'] == 'corrective'])
    predictive_count = len([m for m in maintenance_data if m['maintenance_type'] == 'predictive'])
    
    stats_data = [
        ["Total de mantenimientos", str(len(maintenance_data))],
        ["Preventivos", str(preventive_count)],
        ["Correctivos", str(corrective_count)],
        ["Predictivos", str(predictive_count)],
    ]
    
    stats_table = Table(stats_data, colWidths=[2*inch, 1*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(stats_table)
    elements.append(Spacer(1, 15))
    
    # Detalle de mantenimientos
    elements.append(Paragraph("Detalle de Mantenimientos", styles['Subtitle']))
    
    # Preparar datos para la tabla
    maintenance_details = [["Fecha", "Máquina", "Tipo", "Técnico", "Descripción"]]
    
    for maint in maintenance_data[:10]:  # Limitar a 10 registros para no hacer el PDF muy largo
        machine_name = MONITORING_PARAMS.get(maint['machine_id'], {}).get('name', maint['machine_id'])
        
        # Tipo de mantenimiento formateado
        maint_type = {
            'preventive': 'Preventivo',
            'corrective': 'Correctivo',
            'predictive': 'Predictivo'
        }.get(maint.get('maintenance_type', ''), maint.get('maintenance_type', ''))
        
        maintenance_details.append([
            maint.get('timestamp', '').strftime("%d/%m/%Y") if isinstance(maint.get('timestamp', ''), datetime) else maint.get('timestamp', ''),
            machine_name,
            maint_type,
            maint.get('technician', ''),
            maint.get('description', '')[:50] + ('...' if len(maint.get('description', '')) > 50 else ''),
        ])
    
    # Crear tabla
    maintenance_table = Table(maintenance_details)
    maintenance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(maintenance_table)
    elements.append(Spacer(1, 15))
    
    # Calendario de próximos mantenimientos
    elements.append(Paragraph("Próximos Mantenimientos Programados", styles['Subtitle']))
    
    # Ejemplo de programación (en una implementación real, esto vendría de la base de datos)
    today = datetime.now().date()
    schedule_data = [
        ["Máquina", "Tipo", "Fecha Programada", "Prioridad"]
    ]
    
    # Agregar datos de ejemplo
    for mid, config in MONITORING_PARAMS.items():
        if machine_id == 'all' or machine_id == mid:
            schedule_data.append([
                config['name'],
                "Inspección Rutinaria",
                (today + timedelta(days=15)).strftime("%d/%m/%Y"),
                "Media",
            ])
            schedule_data.append([
                config['name'],
                "Mantenimiento Menor",
                (today + timedelta(days=45)).strftime("%d/%m/%Y"),
                "Baja",
            ])
    
    # Crear tabla
    schedule_table = Table(schedule_data)
    schedule_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(schedule_table)

def _add_performance_report_content(elements, styles, machine_id, start_date, end_date):
    """Agrega contenido específico para el reporte de rendimiento."""
    elements.append(Paragraph("Análisis de Rendimiento", styles['Subtitle']))
    
    # Mensaje de desarrollo
    elements.append(Paragraph("El reporte de análisis de rendimiento está en desarrollo. Próximamente incluirá métricas de eficiencia operativa, tiempos de transición y consumo energético.", styles['Normal']))
    elements.append(Spacer(1, 15))
    
    # Placeholder para el contenido futuro
    elements.append(Paragraph("Estadísticas que se incluirán:", styles['Normal']))
    
    stats_list = [
        "Tiempo promedio de transición",
        "Número de ciclos completados",
        "Consumo energético estimado",
        "Comparativa entre máquinas",
        "Indicadores de eficiencia operativa",
        "Tendencias de rendimiento",
    ]
    
    for stat in stats_list:
        elements.append(Paragraph(f"• {stat}", styles['Normal']))
# Примеры использования интеграции Maintainable

## Настройка компонента

1. Перейдите в **Настройки** → **Устройства и службы**
2. Нажмите **Добавить интеграцию**
3. Найдите **Maintainable** в списке
4. Заполните форму:
   - **Название компонента**: например, "Фильтр питьевой воды"
   - **Интервал обслуживания (дни)**: например, 90
   - **Дата последнего обслуживания**: выберите дату (необязательно)
   - **Привязать к устройству**: выберите устройство из списка (необязательно)

## Создаваемые сущности

После настройки будут созданы следующие сущности:

### Сенсоры
- `sensor.фильтр_питьевой_воды_m_status` - статус обслуживания (ok/due/overdue)
- `sensor.фильтр_питьевой_воды_m_days` - количество дней до обслуживания

### Кнопки
- `button.фильтр_питьевой_воды_maintenance_button` - кнопка выполнения обслуживания

## Автоматизации

### Уведомление о необходимости обслуживания

```yaml
automation:
  - alias: "Уведомление о обслуживании фильтра"
    trigger:
      - platform: state
        entity_id: sensor.фильтр_питьевой_воды_m_status
        to: "due"
    action:
      - service: notify.telegram
        data:
          message: "Требуется обслуживание: {{ trigger.entity_id.split('.')[1].replace('_m_status', '').replace('_', ' ').title() }}"
```

### Уведомление о просроченном обслуживании

```yaml
automation:
  - alias: "Уведомление о просроченном обслуживании"
    trigger:
      - platform: state
        entity_id: sensor.фильтр_питьевой_воды_m_status
        to: "overdue"
    action:
      - service: notify.telegram
        data:
          message: "ВНИМАНИЕ! Просрочено обслуживание: {{ trigger.entity_id.split('.')[1].replace('_m_status', '').replace('_', ' ').title() }}"
```

### Автоматическое выполнение обслуживания по кнопке

```yaml
automation:
  - alias: "Подтверждение обслуживания"
    trigger:
      - platform: state
        entity_id: button.фильтр_питьевой_воды_maintenance_button
    action:
      - service: notify.telegram
        data:
          message: "Обслуживание выполнено: {{ trigger.entity_id.split('.')[1].replace('_maintenance_button', '').replace('_', ' ').title() }}"
```

## Использование сервисов

### Выполнение обслуживания через сервис

```yaml
service: maintainable.perform_maintenance
data:
  entity_id: sensor.фильтр_питьевой_воды_m_status
```

### Установка даты последнего обслуживания

```yaml
service: maintainable.set_last_maintenance
data:
  entity_id: sensor.фильтр_питьевой_воды_m_status
  maintenance_date: "2024-01-15"
```

## События

Интеграция генерирует следующие события:

- `maintainable_due` - когда компонент требует обслуживания (≤7 дней)
- `maintainable_overdue` - когда обслуживание просрочено
- `maintainable_completed` - когда обслуживание выполнено

### Автоматизация на основе событий

```yaml
automation:
  - alias: "Обработка событий обслуживания"
    trigger:
      - platform: event
        event_type: maintainable_due
      - platform: event
        event_type: maintainable_overdue
    action:
      - service: notify.telegram
        data:
          message: >
            Компонент "{{ trigger.event.data.component_name }}" 
            {% if trigger.event.event_type == 'maintainable_due' %}
            требует обслуживания через {{ trigger.event.data.days_until }} дней
            {% else %}
            просрочен на {{ trigger.event.data.days_overdue }} дней
            {% endif %}
``` 
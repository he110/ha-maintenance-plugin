# События интеграции Maintainable

Интеграция Maintainable автоматически отправляет события в шину событий Home Assistant при изменении статуса обслуживания компонентов.

## Типы событий

### `maintainable_overdue`
Отправляется когда компонент переходит в статус "Просрочено" (overdue).

**Данные события:**
```json
{
  "entity_id": "sensor.water_filter_status",
  "name": "Водяной фильтр",
  "old_status": "due",
  "new_status": "overdue",
  "days_remaining": -5,
  "next_maintenance": "2024-01-15T12:00:00+00:00"
}
```

### `maintainable_due`
Отправляется когда компонент переходит в статус "Требует обслуживания" (due) - за 7 дней до истечения срока.

**Данные события:**
```json
{
  "entity_id": "sensor.air_filter_status",
  "name": "Воздушный фильтр",
  "old_status": "ok",
  "new_status": "due",
  "days_remaining": 3,
  "next_maintenance": "2024-01-25T12:00:00+00:00"
}
```

### `maintainable_completed`
Отправляется при выполнении обслуживания (нажатие кнопки или вызов сервиса).

**Данные события:**
```json
{
  "entity_id": "sensor.robot_vacuum_brush_status",
  "name": "Щетка робота-пылесоса",
  "maintenance_date": "2024-01-20T14:30:00+00:00",
  "next_maintenance": "2024-02-19T14:30:00+00:00",
  "days_until_next": 30
}
```

## Использование событий

### Автоматизации
Вы можете создавать автоматизации на основе этих событий:

```yaml
automation:
  - alias: "Уведомление о просроченном обслуживании"
    trigger:
      platform: event
      event_type: maintainable_overdue
    action:
      service: notify.mobile_app_my_phone
      data:
        title: "Просрочено обслуживание!"
        message: "{{ trigger.event.data.name }} требует немедленного обслуживания"
        
  - alias: "Напоминание о предстоящем обслуживании"
    trigger:
      platform: event
      event_type: maintainable_due
    action:
      service: notify.persistent_notification
      data:
        title: "Скоро обслуживание"
        message: "{{ trigger.event.data.name }} потребует обслуживания через {{ trigger.event.data.days_remaining }} дней"
```

### Отключение событий
События можно отключить в настройках компонента:
1. Перейдите в Настройки → Устройства и службы
2. Найдите интеграцию Maintainable
3. Нажмите "Настроить"
4. Снимите галочку "Включить уведомления о событиях"

## Примечания
- События отправляются только при изменении статуса
- События не отправляются если уведомления отключены в настройках
- Все даты в событиях представлены в формате ISO 8601 с часовым поясом 
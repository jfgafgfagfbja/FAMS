def filter_students(query: Query, user: models.User, db: Session) -> Query:
    if user.role in SCHOOL_WIDE_VIEWERS:
        return query
    if user.role in FACULTY_ROLES:
        unit_id = staff_unit_id(user, db)
        return query.filter(models.Student.faculty_id == (unit_id if unit_id is not None else -1))
    if user.role == ROLE_LECTURER:
        lecturer = lecturer_profile(user, db)
        taught = (
            db.query(models.Enrollment.student_id)
            .join(models.Class, models.Class.id == models.Enrollment.class_id)
            .filter(models.Class.lecturer_id == (lecturer.id if lecturer else -1))
        )
        return query.filter(models.Student.id.in_(taught))
    return query.filter(false())

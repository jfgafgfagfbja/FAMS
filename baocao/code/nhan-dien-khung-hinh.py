def recognize_frame(
    db: Session, image_bytes: bytes, class_id: int
) -> list[dict]:
    img = _decode_image(image_bytes)
    faces = get_engine().get(img)
    if not faces:
        return []
    results = []
    for face in faces:
        is_real, liveness_score = (True, 1.0)
        if settings.ANTISPOOF_ENABLED:
            is_real, liveness_score = antispoof_service.check_liveness(img, face.bbox)
        emb = face.normed_embedding.astype(np.float32)
        distance = models.FaceEmbedding.embedding.cosine_distance(emb.tolist())
        match = (
            db.query(models.Enrollment.student_id, distance.label("distance"))
            .join(models.FaceEmbedding,
                  models.FaceEmbedding.student_id == models.Enrollment.student_id)
            .join(models.Student, models.Student.id == models.Enrollment.student_id)
            .filter(models.Enrollment.class_id == class_id,
                    models.FaceEmbedding.status == "approved",
                    models.Student.consent_given.is_(True))
            .order_by(distance)
            .first()
        )
        if match is None:
            results.append({
                "student_id": None, "confidence": 0.0,
                "bbox": face.bbox.astype(int).tolist(),
                "is_spoof": not is_real, "liveness_score": liveness_score,
            })
            continue
        student_id, dist = match
        conf = round(1 - dist, 3)
        results.append({
            "student_id": student_id if conf >= settings.RECOGNITION_THRESHOLD else None,
            "confidence": conf,
            "bbox": face.bbox.astype(int).tolist(),
            "is_spoof": not is_real,
            "liveness_score": liveness_score,
        })
    return results

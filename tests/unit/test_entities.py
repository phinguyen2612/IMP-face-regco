from fr_domain.entities import FaceEnrollment, Person


def test_person_supports_multiple_model_versioned_enrollments() -> None:
    person = Person(
        id="person-1",
        display_name="Example Person",
        enrollments=[
            FaceEnrollment(
                id="enrollment-1",
                embedding=(1.0, 0.0),
                embedding_model_id="adaface",
                embedding_model_version="1.0",
            ),
            FaceEnrollment(
                id="enrollment-2",
                embedding=(0.9, 0.1),
                embedding_model_id="adaface",
                embedding_model_version="1.0",
            ),
        ],
    )

    assert len(person.enrollments) == 2
    assert {item.id for item in person.enrollments} == {"enrollment-1", "enrollment-2"}

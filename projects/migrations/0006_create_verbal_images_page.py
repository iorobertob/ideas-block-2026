from django.db import migrations


def create_verbal_images_page(apps, schema_editor):
    from projects.models import ProjectsIndexPage, VerbalImagesPage

    if VerbalImagesPage.objects.filter(slug="verbal-images").exists():
        return

    projects_index = ProjectsIndexPage.objects.first()
    if not projects_index:
        return

    page = VerbalImagesPage(
        title="Verbal Images in Literature Database",
        slug="verbal-images",
        year=2020,
        status="ongoing",
        project_type="research",
        intro=(
            "A growing annotated database of imageable literary language — "
            "verbal images manually collected from literary criticism across "
            "genres, languages, and centuries."
        ),
        live=True,
    )
    projects_index.add_child(instance=page)


def remove_verbal_images_page(apps, schema_editor):
    from projects.models import VerbalImagesPage
    VerbalImagesPage.objects.filter(slug="verbal-images").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0005_verbalimagespage"),
    ]

    operations = [
        migrations.RunPython(create_verbal_images_page, remove_verbal_images_page),
    ]

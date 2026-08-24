from django.core.management.base import BaseCommand

from scheduler.data.generator import generate_all


class Command(BaseCommand):

    help = "Generate realistic Sridhar Precision Works factory data"

    def handle(self, *args, **options):

        self.stdout.write(
            "Generating factory data..."
        )

        generate_all()

        self.stdout.write(
            self.style.SUCCESS(
                "Factory data generated successfully!"
            )
        )
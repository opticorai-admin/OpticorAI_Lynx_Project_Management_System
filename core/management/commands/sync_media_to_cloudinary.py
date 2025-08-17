from django.core.management.base import BaseCommand, CommandError
from django.core.files import File
from django.conf import settings
from pathlib import Path
import os

from core.models import CustomUser, Task


class Command(BaseCommand):
    help = "Upload existing local media files (avatars, task files) to Cloudinary."

    def add_arguments(self, parser):
        parser.add_argument(
            "--only",
            choices=["all", "avatars", "task_files"],
            default="all",
            help="Which media to sync",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be uploaded without changing anything",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Optional limit of records to process for each model",
        )

    def handle(self, *args, **options):
        # Ensure Cloudinary is configured
        storage_backend = getattr(settings, "DEFAULT_FILE_STORAGE", "")
        cloudinary_url = os.environ.get("CLOUDINARY_URL")
        if not cloudinary_url or "cloudinary_storage" not in storage_backend:
            raise CommandError(
                "Cloudinary is not configured. Set CLOUDINARY_URL and enable Cloudinary storage in settings."
            )

        # Django passes option keys without leading dashes
        only = options["only"]
        dry_run = options["dry_run"]
        limit = options["limit"]

        if only in ("all", "avatars"):
            self._sync_avatars(dry_run=dry_run, limit=limit)

        if only in ("all", "task_files"):
            self._sync_task_files(dry_run=dry_run, limit=limit)

        self.stdout.write(self.style.SUCCESS("Sync complete."))

    def _is_cloudinary_url(self, url: str) -> bool:
        if not url:
            return False
        return "res.cloudinary.com" in url or "cloudinary" in url

    def _sync_avatars(self, dry_run: bool, limit: int | None):
        qs = CustomUser.objects.exclude(avatar="").exclude(avatar=None)
        if limit:
            qs = qs[:limit]

        processed = 0
        uploaded = 0
        skipped = 0

        for user in qs:
            processed += 1
            try:
                url = getattr(user.avatar, "url", "")
                if self._is_cloudinary_url(url):
                    skipped += 1
                    continue

                local_path = getattr(user.avatar, "path", None)
                if not local_path or not os.path.isfile(local_path):
                    skipped += 1
                    continue

                if dry_run:
                    self.stdout.write(f"[DRY-RUN] Would upload avatar for user id={user.id} path={local_path}")
                    continue

                with open(local_path, "rb") as fh:
                    filename = os.path.basename(user.avatar.name)
                    user.avatar.save(filename, File(fh), save=True)
                uploaded += 1
                self.stdout.write(self.style.SUCCESS(f"Uploaded avatar for user id={user.id}"))
            except Exception as exc:
                self.stderr.write(f"Failed avatar upload for user id={getattr(user, 'id', None)}: {exc}")

        self.stdout.write(
            f"Avatars processed={processed} uploaded={uploaded} skipped={skipped}"
        )

    def _sync_task_files(self, dry_run: bool, limit: int | None):
        qs = Task.objects.exclude(file_upload="").exclude(file_upload=None)
        if limit:
            qs = qs[:limit]

        processed = 0
        uploaded = 0
        skipped = 0

        for task in qs:
            processed += 1
            try:
                url = getattr(task.file_upload, "url", "")
                if self._is_cloudinary_url(url):
                    skipped += 1
                    continue

                local_path = getattr(task.file_upload, "path", None)
                if not local_path or not os.path.isfile(local_path):
                    skipped += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        f"[DRY-RUN] Would upload task file for task id={task.id} path={local_path}"
                    )
                    continue

                with open(local_path, "rb") as fh:
                    filename = os.path.basename(task.file_upload.name)
                    task.file_upload.save(filename, File(fh), save=True)
                uploaded += 1
                self.stdout.write(self.style.SUCCESS(f"Uploaded task file for task id={task.id}"))
            except Exception as exc:
                self.stderr.write(
                    f"Failed task file upload for task id={getattr(task, 'id', None)}: {exc}"
                )

        self.stdout.write(
            f"Task files processed={processed} uploaded={uploaded} skipped={skipped}"
        )



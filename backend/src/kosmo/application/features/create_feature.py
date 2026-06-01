from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.feature import Feature, FeatureStatus
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository, ProjectRepository
from kosmo.domain.sdd.document_converters import slugify_spanish
from kosmo.domain.sdd.id_generator import IdGenerator


class CreateFeatureUseCase:
    def __init__(
        self,
        feature_repo: FeatureRepository,
        project_repo: ProjectRepository,
    ) -> None:
        self._feature_repo = feature_repo
        self._project_repo = project_repo

    async def execute(self, project_id: ProjectId, title: str, description: str) -> Feature:
        project = await self._project_repo.get(project_id)
        if project is None:
            raise ProjectNotFoundError(str(project_id))

        slug = slugify_spanish(title, max_length=60)
        existing = await self._feature_repo.get_by_slug(project_id, slug)
        if existing is not None:
            counter = 2
            while True:
                candidate = f"{slug}-{counter}"
                if await self._feature_repo.get_by_slug(project_id, candidate) is None:
                    slug = candidate
                    break
                counter += 1

        feature = Feature(
            id=FeatureId(IdGenerator.generate("feature")),
            project_id=project_id,
            title=title,
            slug=slug,
            description=description,
            status=FeatureStatus.BORRADOR,
        )

        await self._feature_repo.add(feature)
        return feature

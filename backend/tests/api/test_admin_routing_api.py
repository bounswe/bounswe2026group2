from app.main import app


def _route_by_path(path: str):
    return next(route for route in app.routes if getattr(route, "path", None) == path)


class TestAdminRoutingAPI:
    def test_admin_routes_are_exposed_from_admin_router(self):
        admin_paths = {
            "/stories/admin/reports",
            "/stories/admin/reports/{report_id}",
            "/stories/admin/stories/{story_id}",
        }

        routes = {
            route.path: route
            for route in app.routes
            if getattr(route, "path", None) in admin_paths
        }

        assert set(routes) == admin_paths
        assert all(route.endpoint.__module__ == "app.routers.admin" for route in routes.values())

    def test_admin_routes_are_registered_before_story_id_route(self):
        route_paths = [getattr(route, "path", None) for route in app.routes]

        story_detail_index = route_paths.index("/stories/{story_id}")

        assert route_paths.index("/stories/admin/reports") < story_detail_index
        assert route_paths.index("/stories/admin/reports/{report_id}") < story_detail_index
        assert route_paths.index("/stories/admin/stories/{story_id}") < story_detail_index

    def test_story_router_does_not_own_admin_paths(self):
        admin_routes = [
            _route_by_path("/stories/admin/reports"),
            _route_by_path("/stories/admin/reports/{report_id}"),
            _route_by_path("/stories/admin/stories/{story_id}"),
        ]

        assert all(route.endpoint.__module__ != "app.routers.story" for route in admin_routes)

# Publishing py-flowtoken

The release workflow publishes wheels and source distributions to PyPI using GitHub's short-lived OIDC identity. It does not require a stored PyPI token.

## One-time PyPI configuration

In the owning PyPI account, open [Publishing](https://pypi.org/manage/account/publishing/) and add a pending GitHub publisher:

| Field | Value |
| --- | --- |
| PyPI project name | `py-flowtoken` |
| Owner | `jcllobet` |
| Repository name | `py-flowtoken` |
| Workflow name | `publish.yml` |
| Environment name | `pypi` |

After the first successful upload, PyPI converts the pending publisher to a regular publisher for this project. The project belongs to the PyPI account that configured the publisher. This is the maintained distribution of the Python adaptation; it does not imply affiliation with the original npm library.

## Release

1. Update the matching version in `pyproject.toml` and `src/py_flowtoken/__init__.py`.
2. Run the Python and browser checks. Commit the release, then create and push its `v<version>` tag.
3. Run **Publish to PyPI** on that tag, or publish a GitHub Release for the tag. Branch dispatches do not publish.
4. Verify both distribution files appear on PyPI and install the wheel from PyPI in a clean environment.

The workflow checks tag/version agreement, runs Python tests, builds both distributions and validates their metadata before uploading. Uploads run in the GitHub `pypi` environment with only the publishing job granted `id-token: write`.

import json

import pytest

from tests import Stub, copy_fixture
from ventoy_macos import VentoyMacosError
from ventoy_macos.downloader import Downloader

bp = breakpoint


@pytest.fixture
def downloader(tmp_path) -> Downloader:
    """Return a Downloader object."""
    return Downloader(version="1.1.12", workdir=tmp_path)


def test_downloader():
    assert Downloader()


def test_downloader_tarball_path(downloader, tmp_path):
    assert downloader.tarball_path == tmp_path / "ventoy-1.1.12-linux.tar.gz"


def test_downloader_ventoy_dir(downloader, tmp_path):
    assert downloader.ventoy_dir == tmp_path / "ventoy-1.1.12"


def test_downloader_find_ventoy_dir(monkeypatch, downloader, tmp_path):
    ventoy_dir = tmp_path / "ventoy-1.1.12"
    ventoy_dir.mkdir()

    path = tmp_path / "ventoy-1.1.12"

    assert downloader.find_ventoy_dir("1.1.12") == path
    assert downloader.find_ventoy_dir() == path
    assert downloader.find_ventoy_dir("1.1.11") is False


def test_downloader_request(monkeypatch, downloader):
    with monkeypatch.context() as m:
        expected = Stub(ok=True, status_code="200", reason="OK")
        m.setattr("requests.get", lambda *a, **k: expected)

        response = downloader.request("https://jsonplaceholder.typicode.com/posts")

        assert response and response == expected


def test_downloader_request_failed(monkeypatch, downloader):
    with monkeypatch.context() as m:
        response = Stub(ok=False, status_code="400", reason="NOT FOUND")

        m.setattr("requests.get", lambda url, *a, **k: response)

        with pytest.raises(VentoyMacosError) as e:
            downloader.request("https://jsonplaceholder.typicode.com/posts")

        exception = e.value

        message = (
            "Request Failed [400 NOT FOUND]: "
            "https://jsonplaceholder.typicode.com/posts"
        )

        assert str(exception) == message
        assert exception.response and exception.response == response


def test_downloader_get_latest(monkeypatch, downloader):
    """
    WHEN: .get_latest() is called
    THEN: it should return the latest ventoy release version.
    """
    with monkeypatch.context() as m:
        response = Stub(ok=True, json=lambda: json.loads('{"tag_name": "v1.1.12"}'))
        m.setattr("requests.get", lambda url, *a, **k: response)

        tag = downloader.get_latest()

        assert tag == "1.1.12"


def test_downloader_download(tmp_path, monkeypatch, downloader):
    """
    WHEN: .download() is called with a valid ventoy version number and directory
    THEN: the ventoy release for that version should be downloaded to that directory
    """

    with monkeypatch.context() as m:
        expected = Stub(content=b'file contents', ok=True)
        m.setattr("requests.get", lambda url, *a, **k: expected)

        response = downloader.download()

        path = downloader.tarball_path

        assert response == expected
        assert path.is_file() and path.read_bytes() == b"file contents"


def test_downloader_extract(monkeypatch, downloader, tmp_path):
    """
    WHEN: .extract() is called with the path to a tarball and a destination path
    THEN: it should extract the tarball to that destination directory
    """
    copy_fixture("ventoy-1.1.12-linux.tar.gz", tmp_path)

    downloader.extract()

    assert downloader.ventoy_dir.is_dir()


#  @pytest.mark.skip
#  def test_downloader_():
#      ...

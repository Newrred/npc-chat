from types import SimpleNamespace

import pytest

from scripts.build_installer import build


def args(tmp_path, **kw):
    values = dict(output=tmp_path/'out', package=tmp_path/'missing-package', release_id='1.4.0-test',
                  distribution='internal', app_url=None, model_url=None)
    values.update(kw)
    return SimpleNamespace(**values)


def test_release_builder_rejected_before_reading_or_writing(tmp_path):
    with pytest.raises(ValueError, match='disabled'):
        build(args(tmp_path, distribution='release'))
    assert not (tmp_path/'out').exists()


def test_existing_build_output_never_overwritten(tmp_path):
    output = tmp_path/'out'
    output.mkdir()
    sentinel = output/'keep'
    sentinel.write_text('keep')
    with pytest.raises(ValueError, match='new output'):
        build(args(tmp_path))
    assert sentinel.read_text() == 'keep'


@pytest.mark.parametrize('url', ['http://example.test/file', 'https://user:password@example.test/file',
                                'https://example.test/file?token=private', 'https://example.test/file#fragment'])
def test_unsafe_download_source_rejected(tmp_path, url):
    with pytest.raises(ValueError, match='HTTPS'):
        build(args(tmp_path, app_url=url, model_url='https://example.test/model'))
    assert not (tmp_path/'out').exists()


def test_partial_download_configuration_rejected(tmp_path):
    with pytest.raises(ValueError, match='Both'):
        build(args(tmp_path, app_url='https://example.test/app'))
    assert not (tmp_path/'out').exists()

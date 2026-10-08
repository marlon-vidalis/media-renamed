import pytest
from pathlib import Path
from media_renamed.core.renamer import rename_media, find_subtitle


def test_rename_simples(tmp_path):
    src = tmp_path / "arquivo.mkv"
    dst = tmp_path / "Novo Nome.mkv"
    src.touch()
    rename_media(src, dst)
    assert dst.exists()
    assert not src.exists()


def test_rename_com_legenda(tmp_path):
    src = tmp_path / "arquivo.mkv"
    sub = tmp_path / "arquivo.srt"
    dst = tmp_path / "Novo Nome.mkv"
    src.touch()
    sub.touch()
    rename_media(src, dst, sub)
    assert dst.exists()
    assert (tmp_path / "Novo Nome.srt").exists()
    assert not src.exists()
    assert not sub.exists()


def test_rename_colisao(tmp_path):
    src = tmp_path / "arquivo.mkv"
    dst = tmp_path / "existente.mkv"
    src.touch()
    dst.touch()
    with pytest.raises(FileExistsError):
        rename_media(src, dst)


def test_rename_rollback_se_legenda_falhar(tmp_path):
    """Se a legenda falhar, o vídeo deve voltar ao nome original."""
    src = tmp_path / "arquivo.mkv"
    sub = tmp_path / "arquivo.srt"
    dst = tmp_path / "Novo Nome.mkv"
    dst_sub = tmp_path / "Novo Nome.srt"
    src.touch()
    sub.touch()
    dst_sub.touch()  # força colisão na legenda
    with pytest.raises(FileExistsError):
        rename_media(src, dst, sub)
    assert src.exists()   # rollback ok
    assert not dst.exists()


def test_find_subtitle_srt(tmp_path):
    video = tmp_path / "filme.mkv"
    sub = tmp_path / "filme.srt"
    video.touch()
    sub.touch()
    assert find_subtitle(video) == sub


def test_find_subtitle_ass(tmp_path):
    video = tmp_path / "filme.mkv"
    sub = tmp_path / "filme.ass"
    video.touch()
    sub.touch()
    assert find_subtitle(video) == sub


def test_find_subtitle_ausente(tmp_path):
    video = tmp_path / "filme.mkv"
    video.touch()
    assert find_subtitle(video) is None

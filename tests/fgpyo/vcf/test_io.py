from pathlib import Path

import pytest

from fgpyo.vcf import reader as vcf_reader
from fgpyo.vcf import writer as vcf_writer
from fgpyo.vcf.builder import VariantBuilder


@pytest.fixture(scope="function")
def vcf_path(tmp_path: Path) -> Path:
    builder = VariantBuilder()
    builder.add()
    return builder.to_path(path=tmp_path / "test.vcf.gz")


def test_reader_closes_on_exception(vcf_path: Path) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        with vcf_reader(vcf_path) as r:
            raise RuntimeError("boom")
    assert r.closed is True


def test_writer_closes_on_exception(tmp_path: Path) -> None:
    header = VariantBuilder().header
    out = tmp_path / "out.vcf"
    with pytest.raises(RuntimeError, match="boom"):
        with vcf_writer(out, header=header) as w:
            raise RuntimeError("boom")
    assert w.closed is True


def test_reader_accepts_file_handle(vcf_path: Path) -> None:
    with open(vcf_path, "rb") as handle:
        with vcf_reader(handle) as r:
            records = list(r)
    assert len(records) == 1


def test_reader_rejects_non_path_non_handle() -> None:
    with pytest.raises(TypeError, match="Cannot open"):
        with vcf_reader(123):  # type: ignore[arg-type]
            pass


def test_writer_rejects_non_path_non_handle() -> None:
    header = VariantBuilder().header
    with pytest.raises(TypeError, match="Cannot open"):
        with vcf_writer(123, header=header):  # type: ignore[arg-type]
            pass


_BGZF_MAGIC = b"\x1f\x8b"


def test_writer_file_handle_bgzipped_round_trip(tmp_path: Path) -> None:
    builder = VariantBuilder()
    record = builder.add()
    out = tmp_path / "out.vcf.gz"
    with open(out, "wb") as handle:
        with vcf_writer(handle, header=builder.header, mode="wz") as w:
            w.write(record)
    assert out.read_bytes()[:2] == _BGZF_MAGIC
    with vcf_reader(out) as r:
        records = list(r)
    assert len(records) == 1


def test_writer_default_mode_autodetects_bgzip(tmp_path: Path) -> None:
    builder = VariantBuilder()
    record = builder.add()
    out = tmp_path / "out.vcf.gz"
    with vcf_writer(out, header=builder.header) as w:
        w.write(record)
    assert out.read_bytes()[:2] == _BGZF_MAGIC

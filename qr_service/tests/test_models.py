from qr_service import models


def test_qrcode_table_name():
    assert models.QRCode.__tablename__ == 'qr_codes'

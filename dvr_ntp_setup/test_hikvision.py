"""
test_hikvision.py — Tests unitarios para la lógica de decisión NTP.
Mockea todas las llamadas HTTP; no requiere DVRs reales ni red.

Ejecutar:
  cd HikvisionAnalisisIA
  python -m pytest dvr_ntp_setup/test_hikvision.py -v
"""

import unittest
from unittest.mock import patch, MagicMock

# ─────────────────────────────────────────────────────────────
# Fixtures de DVR de prueba
# ─────────────────────────────────────────────────────────────

DVR_OK = {
    'cod_sucursal':    2,
    'nombre_sucursal': 'León',
    'portal_ip_local': '192.168.1.20',
    'portal_usuario':  'admin',
    'portal_clave':    'abcd1234',
    'puerto_http_vps': 0,
}

# ─────────────────────────────────────────────────────────────
# XML de respuesta simulados
# ─────────────────────────────────────────────────────────────

XML_TIME_MANUAL = """\
<?xml version="1.0" encoding="UTF-8"?>
<Time version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
  <timeMode>manual</timeMode>
  <timeZone>CST+6:00:00</timeZone>
</Time>"""

XML_TIME_NTP = """\
<?xml version="1.0" encoding="UTF-8"?>
<Time version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
  <timeMode>NTP</timeMode>
  <timeZone>CST+6:00:00</timeZone>
</Time>"""

XML_NTP_GOOGLE = """\
<?xml version="1.0" encoding="UTF-8"?>
<NTPServer version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
  <id>1</id>
  <addressingFormatType>hostname</addressingFormatType>
  <hostName>time.google.com</hostName>
  <portNo>123</portNo>
  <synchronizeInterval>60</synchronizeInterval>
</NTPServer>"""

XML_NTP_OTHER = """\
<?xml version="1.0" encoding="UTF-8"?>
<NTPServer version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
  <id>1</id>
  <addressingFormatType>hostname</addressingFormatType>
  <hostName>pool.ntp.org</hostName>
  <portNo>123</portNo>
  <synchronizeInterval>1440</synchronizeInterval>
</NTPServer>"""

XML_NTP_WRONG_TZ = """\
<?xml version="1.0" encoding="UTF-8"?>
<Time version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
  <timeMode>NTP</timeMode>
  <timeZone>CST-6:00:00</timeZone>
</Time>"""


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _mock_response(text: str, status: int = 200) -> MagicMock:
    """Crea un mock de requests.Response."""
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    resp.raise_for_status = MagicMock()  # no lanza nada
    return resp


def _mock_response_401() -> MagicMock:
    import requests
    resp = MagicMock()
    resp.status_code = 401
    resp.text = '<statusCode>401</statusCode>'
    http_err = requests.exceptions.HTTPError(response=resp)
    resp.raise_for_status = MagicMock(side_effect=http_err)
    return resp


# ─────────────────────────────────────────────────────────────
# Tests de hikvision.py (lógica de parseo)
# ─────────────────────────────────────────────────────────────

class TestGetTime(unittest.TestCase):

    @patch('dvr_ntp_setup.hikvision.requests.get')
    def test_parsea_time_mode_manual(self, mock_get):
        mock_get.return_value = _mock_response(XML_TIME_MANUAL)
        from dvr_ntp_setup.hikvision import get_time
        info = get_time(DVR_OK)
        self.assertEqual(info.time_mode, 'manual')
        self.assertEqual(info.time_zone, 'CST+6:00:00')

    @patch('dvr_ntp_setup.hikvision.requests.get')
    def test_parsea_time_mode_ntp(self, mock_get):
        mock_get.return_value = _mock_response(XML_TIME_NTP)
        from dvr_ntp_setup.hikvision import get_time
        info = get_time(DVR_OK)
        self.assertEqual(info.time_mode, 'NTP')

    @patch('dvr_ntp_setup.hikvision.requests.get')
    def test_401_lanza_http_error(self, mock_get):
        mock_get.return_value = _mock_response_401()
        import requests as req
        from dvr_ntp_setup.hikvision import get_time
        with self.assertRaises(req.exceptions.HTTPError):
            get_time(DVR_OK)

    @patch('dvr_ntp_setup.hikvision.requests.get')
    def test_timeout_lanza_timeout(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.Timeout()
        from dvr_ntp_setup.hikvision import get_time
        with self.assertRaises(req.exceptions.Timeout):
            get_time(DVR_OK)


class TestGetNtpServer(unittest.TestCase):

    @patch('dvr_ntp_setup.hikvision.requests.get')
    def test_parsea_ntp_google(self, mock_get):
        mock_get.return_value = _mock_response(XML_NTP_GOOGLE)
        from dvr_ntp_setup.hikvision import get_ntp_server
        info = get_ntp_server(DVR_OK)
        self.assertEqual(info.host_name, 'time.google.com')
        self.assertEqual(info.port, 123)
        self.assertEqual(info.interval, 60)

    @patch('dvr_ntp_setup.hikvision.requests.get')
    def test_parsea_ntp_otro(self, mock_get):
        mock_get.return_value = _mock_response(XML_NTP_OTHER)
        from dvr_ntp_setup.hikvision import get_ntp_server
        info = get_ntp_server(DVR_OK)
        self.assertEqual(info.host_name, 'pool.ntp.org')


class TestIsAlreadyOk(unittest.TestCase):

    def _time_ntp(self):
        from dvr_ntp_setup.hikvision import TimeInfo
        return TimeInfo(time_mode='NTP', time_zone='CST+6:00:00')

    def _time_manual(self):
        from dvr_ntp_setup.hikvision import TimeInfo
        return TimeInfo(time_mode='manual', time_zone='CST+6:00:00')

    def _ntp_google(self):
        from dvr_ntp_setup.hikvision import NtpServerInfo
        return NtpServerInfo(host_name='time.google.com', port=123, interval=60)

    def _ntp_other(self):
        from dvr_ntp_setup.hikvision import NtpServerInfo
        return NtpServerInfo(host_name='pool.ntp.org', port=123, interval=1440)

    def test_ya_correcto_retorna_true(self):
        from dvr_ntp_setup.hikvision import is_already_ok
        self.assertTrue(is_already_ok(self._time_ntp(), self._ntp_google()))

    def test_modo_manual_retorna_false(self):
        from dvr_ntp_setup.hikvision import is_already_ok
        self.assertFalse(is_already_ok(self._time_manual(), self._ntp_google()))

    def test_ntp_otro_servidor_retorna_false(self):
        from dvr_ntp_setup.hikvision import is_already_ok
        self.assertFalse(is_already_ok(self._time_ntp(), self._ntp_other()))

    def test_ntp_correcto_tz_incorrecta_retorna_false(self):
        from dvr_ntp_setup.hikvision import TimeInfo, NtpServerInfo, is_already_ok
        time_bad_tz = TimeInfo(time_mode='NTP', time_zone='CST-6:00:00')
        self.assertFalse(is_already_ok(time_bad_tz, self._ntp_google()))


# ─────────────────────────────────────────────────────────────
# Tests de main.py (lógica de decisión por DVR)
# ─────────────────────────────────────────────────────────────

class TestProcesarDvr(unittest.TestCase):
    """Verifica la lógica de decisión en _procesar_dvr sin tocar red."""

    def _run(self, dry_run=False, **patches):
        """Ejecuta _procesar_dvr con los mocks dados."""
        from dvr_ntp_setup.main import _procesar_dvr
        with patch('dvr_ntp_setup.main.get_time', patches.get('get_time', MagicMock())), \
             patch('dvr_ntp_setup.main.get_ntp_server', patches.get('get_ntp_server', MagicMock())), \
             patch('dvr_ntp_setup.main.set_time_ntp', patches.get('set_time_ntp', MagicMock())), \
             patch('dvr_ntp_setup.main.set_ntp_server', patches.get('set_ntp_server', MagicMock())):
            return _procesar_dvr(DVR_OK, dry_run=dry_run)

    def _time_info(self, mode='NTP', tz='CST+6:00:00'):
        from dvr_ntp_setup.hikvision import TimeInfo
        return TimeInfo(time_mode=mode, time_zone=tz)

    def _ntp_info(self, host='time.google.com'):
        from dvr_ntp_setup.hikvision import NtpServerInfo
        return NtpServerInfo(host_name=host, port=123, interval=60)

    # ── Ya está correcto → ALREADY_OK ────────────────────────

    def test_already_ok_skip_puts(self):
        set_time_mock = MagicMock()
        set_ntp_mock  = MagicMock()
        result = self._run(
            get_time=MagicMock(return_value=self._time_info('NTP')),
            get_ntp_server=MagicMock(return_value=self._ntp_info('time.google.com')),
            set_time_ntp=set_time_mock,
            set_ntp_server=set_ntp_mock,
        )
        self.assertEqual(result['resultado'], 'ALREADY_OK')
        set_time_mock.assert_not_called()
        set_ntp_mock.assert_not_called()

    # ── Modo manual → configurar → SUCCESS ───────────────────

    def test_modo_manual_configura_y_success(self):
        call_count = {'n': 0}

        def get_time_side(*a, **kw):
            call_count['n'] += 1
            if call_count['n'] == 1:
                return self._time_info('manual')   # primera llamada: manual
            return self._time_info('NTP')           # segunda (verificación): NTP

        def get_ntp_side(*a, **kw):
            if call_count['n'] <= 1:
                return self._ntp_info('pool.ntp.org')
            return self._ntp_info('time.google.com')

        result = self._run(
            get_time=MagicMock(side_effect=get_time_side),
            get_ntp_server=MagicMock(side_effect=get_ntp_side),
        )
        self.assertEqual(result['resultado'], 'SUCCESS')

    # ── Timeout → UNREACHABLE ─────────────────────────────────

    def test_timeout_marca_unreachable(self):
        import requests as req
        result = self._run(
            get_time=MagicMock(side_effect=req.exceptions.Timeout()),
        )
        self.assertEqual(result['resultado'], 'UNREACHABLE')
        self.assertIn('timeout', result['error'].lower())

    # ── 401 → AUTH_ERROR ─────────────────────────────────────

    def test_401_marca_auth_error(self):
        import requests as req
        resp = MagicMock()
        resp.status_code = 401
        exc = req.exceptions.HTTPError(response=resp)
        result = self._run(
            get_time=MagicMock(side_effect=exc),
        )
        self.assertEqual(result['resultado'], 'AUTH_ERROR')

    # ── Dry-run → no llama a PUT ──────────────────────────────

    def test_dry_run_no_hace_puts(self):
        set_time_mock = MagicMock()
        set_ntp_mock  = MagicMock()
        result = self._run(
            dry_run=True,
            get_time=MagicMock(return_value=self._time_info('manual')),
            get_ntp_server=MagicMock(return_value=self._ntp_info('pool.ntp.org')),
            set_time_ntp=set_time_mock,
            set_ntp_server=set_ntp_mock,
        )
        set_time_mock.assert_not_called()
        set_ntp_mock.assert_not_called()
        self.assertEqual(result['resultado'], 'SUCCESS')

    # ── PUT NtpServer falla → PARTIAL ────────────────────────

    def test_put_ntp_server_falla_marca_partial(self):
        result = self._run(
            get_time=MagicMock(return_value=self._time_info('manual')),
            get_ntp_server=MagicMock(return_value=self._ntp_info('pool.ntp.org')),
            set_time_ntp=MagicMock(),
            set_ntp_server=MagicMock(side_effect=Exception("Network error")),
        )
        self.assertEqual(result['resultado'], 'PARTIAL')


if __name__ == '__main__':
    unittest.main(verbosity=2)

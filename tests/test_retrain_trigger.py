import pytest
from unittest.mock import patch, MagicMock
from src.retrain_trigger import check_drift_and_retrain

@patch("src.retrain_trigger.train_model")
@patch("src.retrain_trigger.calculate_psi")
@patch("src.retrain_trigger._log_system_alert")
def test_drift_trigger_high_psi(mock_log, mock_calc_psi, mock_train):
    # Mock PSI to be high (e.g. 0.30)
    mock_calc_psi.return_value = 0.30
    
    check_drift_and_retrain()
    
    # Assert retraining was triggered
    mock_train.assert_called_once()
    mock_log.assert_called_once()

@patch("src.retrain_trigger.train_model")
@patch("src.retrain_trigger.calculate_psi")
@patch("src.retrain_trigger._log_system_alert")
def test_drift_trigger_low_psi(mock_log, mock_calc_psi, mock_train):
    # Mock PSI to be low (e.g. 0.10)
    mock_calc_psi.return_value = 0.10
    
    check_drift_and_retrain()
    
    # Assert retraining was NOT triggered
    mock_train.assert_not_called()
    mock_log.assert_not_called()

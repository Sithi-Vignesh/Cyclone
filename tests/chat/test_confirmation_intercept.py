import pytest
from unittest.mock import patch, MagicMock
import app.backend.chat.chain as chain
from app.backend.chat import confirmation


@patch.object(chain, "invoke_chain")
@patch.object(chain, "shutdown_system")
def test_intercept_skips_llm(mock_shutdown_tool, mock_invoke_chain):
    confirmation.clear_confirmation()

    mock_shutdown_tool.invoke.return_value = "Shutting down now."

    token = confirmation.request_confirmation("shutdown")

    result = chain.chat(token)

    assert result == "Shutting down now."
    mock_shutdown_tool.invoke.assert_called_once_with({"token": token})
    mock_invoke_chain.assert_not_called()


@patch.object(chain, "invoke_chain")
def test_no_intercept_calls_llm(mock_invoke_chain):
    from app.backend.chat.schemas import CycloneResponse

    confirmation.clear_confirmation()

    mock_response = CycloneResponse(message="Normal response", schedule_event=None, tool_calls=[], use_agent=False)
    mock_invoke_chain.return_value = mock_response

    result = chain.chat("hello")

    assert result == "Normal response"
    mock_invoke_chain.assert_called_once()
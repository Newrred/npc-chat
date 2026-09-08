class ChatError(RuntimeError):
    def __init__(self, code, message, status=409, retryable=False):
        super().__init__(message)
        self.code, self.message, self.status, self.retryable = code, message, status, retryable


def conflict():
    return ChatError("DUPLICATE_TURN_CONFLICT", "같은 요청 번호의 내용이 달라졌습니다.")

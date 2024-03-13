class UnexpectedDataType(Exception):
    def __init__(
        self,
        current_data_type,
        expected_data_type,
        *args: object,
    ) -> None:
        self.message = (
            "Expected the datatype: "
            + str(expected_data_type)
            + " but received the datatype: "
            + str(current_data_type)
            + " instead."
        )
        super().__init__(self.message, *args)


class MisconfigurationError(Exception):
    pass


class UnexpectedCase(Exception):
    pass


class IllogicalSimulationState(Exception):
    pass


class IllogicalFunctionCall(Exception):
    pass


class UnexpectedBehaviorWarning(Warning):
    pass


class LoadProfileInconsistencyWarning(Warning):
    pass

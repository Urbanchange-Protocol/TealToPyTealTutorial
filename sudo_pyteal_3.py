from pyteal import *

def approval_program():
    gstate = Bytes("gstate")
    recovery = Bytes("recovery")
    wait_time = Bytes("wait_time")
    vault = Bytes("vault")
    amount = Bytes("amount")
    receiver = Bytes("receiver")
    request_time = Bytes("request_time")

    create_vault_checks = And(
        If(Global.group_size() == Int(1)).Else(not_create),
        If(Txn.application_id() == Int(0)).Else(not_create),
        If(Txn.application_args.length() == Int(3)).Else(not_create),
        If(Txn.application_args[0] == Bytes("vault")).Else(not_create),
    )

    create_vault = Seq(
        # change the contract state
        App.globalPut(gstate, "init_escrow"),
        App.globalPut(recovery, Txn.application_args[1]),
        App.globalPut(wait_time, Btoi(Txn.application_args[2])),
        Approve(),
    )
    
	

    not_create_checks = And(
        If(Global.group_size() == Int(2)).Else(not_setescrow),
        If(App.globalGet(gstate) == Bytes("init_escrow")).Else(not_setescrow),
        If(Txn.on_completion() == OnComplete.NoOp).Else(not_setescrow),
        If(Txn.application_args.length() == Int(2)).Else(not_setescrow),
        If(Txn.application_args[0] == Bytes("set_escrow")).Else(not_setescrow),
        If(Txn.sender() == Global.creator_address()).Else(not_setescrow),
        If(Gtxn[0].type_enum() == TxnType.Payment).Else(not_setescrow),
        If(Gtxn[0].amount() == Int(100000)).Else(not_setescrow),
        If(Gtxn[0].receiver() == Txn.application_args[1]).Else(not_setescrow),
        If(Gtxn[0].close_remainder_to() == Global.zero_address()).Else(not_setescrow),
    )

    not_create = Seq(
        # change the contract state
        App.globalPut(gstate, Bytes("waiting")),
        App.globalPut(vault, Txn.application_args[1]),
        Approve(),
    )

	not_setescrow_checks = And(
        If(Global.group_size() == Int(1)).Else(not_withdraw),
        If(App.globalGet(gstate) == Bytes("waiting")).Else(not_withdraw),
        If(Txn.on_completion() == OnComplete.NoOp).Else(not_withdraw),
        If(Txn.application_args.length() == Int(3)).Else(not_withdraw),
        If(Txn.application_args[0] == Bytes("withdraw")).Else(not_withdraw),
        If(Txn.sender() == Global.creator_address()).Else(not_withdraw),
    )
    
    not_setescrow = Seq(
        # change contract state
        App.globalPut(gstate, Bytes("requested")),
        App.globalPut(amount, Btoi(Txn.application_args[1])),
        App.globalPut(receiver, Txn.application_args[2]),
        App.globalPut(request_time, Global.round()),
        Approve(),
    )

    # finalizing a withdrawal
    not_withdraw_checks = And(
        If(Global.group_size() == Int(2)).Else(not_finalize),
        If(App.globalGet(gstate) == Bytes("requested")).Else(not_finalize),
        If(Txn.on_completion() == OnComplete.NoOp).Else(not_finalize),
        If(Txn.application_args.length() == Int(1)).Else(not_finalize),
        If(Txn.application_args[0] == Bytes("finalize")).Else(not_finalize),
        If(App.globalGet("request_time") + App.globalGet("wait_time") >= Global.round()).Else(not_finalize),
        If(Txn.sender() == Global.creator_address()).Else(not_finalize),
        If(Gtxn[0].type_enum() == TxnType.Payment).Else(not_finalize),
        If(Gtxn[0].amount() == App.globalGet(amount)).Else(not_finalize),
        If(Gtxn[0].sender() == App.globalGet(vault)).Else(not_finalize),
        If(Gtxn[0].receiver() == App.globalGet(receiver)).Else(not_finalize),
        If(Gtxn[0].close_remainder_to() == Global.zero_address()).Else(not_finalize),
    )

    not_withdrawal = Seq(
        # change contract state
        App.globalPut(gstate, Bytes("waiting")),
        Approve(),
    )
	

    # cancelling a withdrawal
    not_finalize_checks = And(
        If(Global.group_size() == Int(1)).Else(not_cancel),
        If(App.globalGet(gstate) == Bytes("requested")).Else(not_cancel),
        If(Txn.on_completion() == OnComplete.NoOp).Else(not_cancel),
        If(Txn.application_args.length() == Int(1)).Else(not_cancel),
        If(Txn.application_args[0] == Bytes("cancel")).Else(not_cancel),
        If(Txn.sender() == App.globalGet(recovery)).Else(not_cancel),
    )
    
    not_finalized = Seq(
        # change contract state
        App.globalPut(gstate, Bytes("waiting")),
        Approve(),
    )

    program = Cond(
	[create_vault_checks, create_vault],
	[not_create_checks, not_create],
	[not_setescrow_checks, not_setescrow],
	[not_withdraw_checks, not_withdraw],
	[not_finalize_checks, not_finalize],
	# error if reached (not_cancel)
    )
	
    return compileTeal(program, Mode.Application, version=4)

def clear_state_program():
    program = Return(Int(1))
	
    return compileTeal(program, Mode.Application, version=4)

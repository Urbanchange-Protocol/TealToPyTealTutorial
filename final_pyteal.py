from pyteal import *

def approval_program():
	gstate = Bytes("gstate")
	recovery = Bytes("recovery")
	wait_time = Bytes("wait_time")
	vault = Bytes("vault")
	amount = Bytes("amount")
	receiver = Bytes("receiver")
	request_time = Bytes("request_time")
	
	# creating the vault checks -> not_create
	create_vault_checks = And(
		Global.group_size() == Int(1),
		Txn.application_id() == Int(0),
		Txn.application_args.length() == Int(3),
		Txn.application_args[0] == Bytes("vault"),
	)

	create_vault = Seq(
		# change the contract state
		App.globalPut(gstate, Bytes("init_escrow")),
		App.globalPut(recovery, Txn.application_args[1]),
		App.globalPut(wait_time, Btoi(Txn.application_args[2])),
		Approve(),
	)

	# initializing the escrow
	not_create_checks = And(
		Global.group_size() == Int(2),
		App.globalGet(gstate) == Bytes("init_escrow"),
		Txn.on_completion() == OnComplete.NoOp,
		Txn.application_args.length() == Int(2),
		Txn.application_args[0] == Bytes("set_escrow"),
		Txn.sender() == Global.creator_address(),
		Gtxn[0].type_enum() == TxnType.Payment,
		Gtxn[0].amount() == Int(100000),
		Gtxn[0].receiver() == Txn.application_args[1],
		Gtxn[0].close_remainder_to() == Global.zero_address(),
	)
	not_create = Seq(
		# change the contract state
		App.globalPut(gstate, Bytes("waiting")),
		App.globalPut(vault, Txn.application_args[1]),
		Approve(),
	)

	# request withdrawal
	not_setescrow_checks = And(
		Global.group_size() == Int(1),
		App.globalGet(gstate) == Bytes("waiting"),
		Txn.on_completion() == OnComplete.NoOp,
		Txn.application_args.length() == Int(3),
		Txn.application_args[0] == Bytes("withdraw"),
		Txn.sender() == Global.creator_address(),
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
		Global.group_size() == Int(2),
		App.globalGet(gstate) == Bytes("requested"),
		Txn.on_completion() == OnComplete.NoOp,
		Txn.application_args.length() == Int(1),
		Txn.application_args[0] == Bytes("finalize"),
		App.globalGet(request_time) + App.globalGet(wait_time) >= Global.round(),
		Txn.sender() == Global.creator_address(),
		Gtxn[0].type_enum() == TxnType.Payment,
		Gtxn[0].amount() == App.globalGet(amount),
		Gtxn[0].sender() == App.globalGet(vault),
		Gtxn[0].receiver() == App.globalGet(receiver),
		Gtxn[0].close_remainder_to() == Global.zero_address(),
	)
	not_withdraw = Seq(
		# change contract state
		App.globalPut(gstate, Bytes("waiting")),
		Approve(),
	)

	# cancelling a withdrawal
	not_finalize_checks = And(
		Global.group_size() == Int(1),
		App.globalGet(gstate) == Bytes("requested"),
		Txn.on_completion() == OnComplete.NoOp,
		Txn.application_args.length() == Int(1),
		Txn.application_args[0] == Bytes("cancel"),
		Txn.sender() == App.globalGet(recovery),
	)
	not_finalize = Seq(
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
	program = Err()
	
	return compileTeal(program, Mode.Application, version=4)
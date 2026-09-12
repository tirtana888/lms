<template>
	<FormShell :title="__('Add New Member')" size="lg" @close="close">
		<template #default>
			<div v-if="refusal" class="p-4 text-base text-ink-gray-6">
				{{ refusal }}
			</div>
			<div v-else data-testid="member-fields" class="space-y-4">
				<FormControl
					v-model="member.email"
					:label="__('Email')"
					placeholder="jane@doe.com"
					type="email"
					required
					@keyup.enter="submit()"
				/>
				<div class="flex items-center gap-3">
					<FormControl
						v-model="member.first_name"
						:label="__('First Name')"
						placeholder="Jane"
						type="text"
						class="w-full"
					/>
					<FormControl
						v-model="member.last_name"
						:label="__('Last Name')"
						placeholder="Doe"
						type="text"
						class="w-full"
					/>
				</div>
				<div class="flex flex-col gap-2">
					<div class="text-p-sm-medium text-ink-gray-7">
						{{ __('Roles') }}
					</div>
					<div class="grid md:grid-cols-2 gap-x-6 gap-y-3">
						<BooleanSwitch
							size="sm"
							:label="__('Student')"
							v-model="roles.lms_student"
						/>
						<BooleanSwitch
							size="sm"
							:label="__('Course Creator')"
							v-model="roles.course_creator"
						/>
						<BooleanSwitch
							size="sm"
							:label="__('Evaluator')"
							v-model="roles.batch_evaluator"
						/>
						<BooleanSwitch
							size="sm"
							:label="__('Moderator')"
							v-model="roles.moderator"
						/>
					</div>
				</div>
			</div>
		</template>
		<template #actions>
			<div v-if="!refusal" class="flex items-center justify-end">
				<HeaderButton
					data-testid="member-save"
					:label="__('Save')"
					variant="solid"
					:loading="submitting"
					@click="submit()"
				/>
			</div>
		</template>
	</FormShell>
</template>
<script setup lang="ts">
import { call, FormControl, toast } from 'frappe-ui'
import { computed, inject, reactive, ref } from 'vue'
import { useOnboarding, useTelemetry } from 'frappe-ui/frappe'
import BooleanSwitch from '@/components/Controls/BooleanSwitch.vue'
import FormShell from '@/components/FormShell.vue'
import HeaderButton from '@/components/HeaderButton.vue'
import { useFormRoute } from '@/composables/useFormRoute'
import { notifyMembersChanged } from '@/stores/members'
import { cleanError } from '@/utils'
import type { SessionUser } from '@/types'

const user = inject<SessionUser>('$user')!
const { capture } = useTelemetry()
const { updateOnboardingStep } = useOnboarding('learning')

// Only reached on a deep link or a reload — opened from Members.vue this pops
// back to the list (useFormRoute.ts); Members is this route's own parent.
const { close } = useFormRoute({ name: 'Members' })

// Members.vue's Add button carried no gate of its own — the gate was on the
// settings surface around it, and a URL goes through neither. `is_moderator`
// alone, deliberately: this is the narrowest gate in settings and
// get_members/save_role both `frappe.only_for("Moderator")`.
const refusal = computed(() => {
	if ((window as Window & { read_only_mode?: boolean }).read_only_mode)
		return __('This site is in read-only mode.')
	if (!user.data?.is_moderator)
		return __('You are not permitted to manage members.')
	return ''
})

const ROLE_MAP: Record<string, string> = {
	moderator: 'Moderator',
	course_creator: 'Course Creator',
	batch_evaluator: 'Batch Evaluator',
	lms_student: 'LMS Student',
}

const member = reactive({ email: '', first_name: '', last_name: '' })

const roles = reactive({
	moderator: false,
	course_creator: false,
	batch_evaluator: false,
	lms_student: false,
})

const submitting = ref(false)

const errorMessage = (err: { messages?: string[] }, fallback: string): string =>
	cleanError(err.messages?.[0]) || fallback

const assignRoles = async (userEmail: string) => {
	for (const [key, checked] of Object.entries(roles)) {
		if (checked)
			await call('lms.lms.api.save_role', {
				user: userEmail,
				role: ROLE_MAP[key],
				value: 1,
			})
	}
}

const submit = async () => {
	if (refusal.value || submitting.value) return
	if (!member.email?.trim()) {
		toast.error(__('Email is required'))
		return
	}

	submitting.value = true
	try {
		const created = await call('frappe.client.insert', {
			doc: {
				doctype: 'User',
				email: member.email.trim(),
				first_name: member.first_name.trim() || undefined,
				last_name: member.last_name.trim() || undefined,
			},
		})

		await assignRoles(created.name)

		if (user.data?.is_system_manager) updateOnboardingStep('invite_students')
		capture('user_added')
		toast.success(__('Member added successfully'))
		notifyMembersChanged()
		close()
	} catch (err: any) {
		toast.error(errorMessage(err, __('Unable to add member')))
	} finally {
		submitting.value = false
	}
}
</script>

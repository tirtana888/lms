import frappe

# (event_key, Email Template name, subject as Jinja, body copied verbatim from
# the matching lms/templates/emails/*.html file)
#
# Deliberately does NOT set LMS Email Notification.custom_template for any of
# these - only makes the current built-in wording visible and editable in
# Settings > Email > Templates. Every event keeps sending exactly what it
# sends today (the file-based default) until an admin explicitly picks one of
# these in Settings > Email > Notifications. batch_start_reminder is the
# clearest reason not to auto-activate: that one event renders two different
# texts today (live class vs. self-paced) depending on the batch, and forcing
# a single seeded template into custom_template would silently collapse that
# distinction the moment this patch ran, not because an admin asked for it.
_DEFAULT_TEMPLATES = {
	"published_course": (
		"Course Published",
		'{{ _("A new course has been published on") }} {{ brand_name }}',
		"""<div style="width: 70%; margin: 0 auto;">
    <img src="{{ brand_logo }}" style="width: 30px; height: 30px;" />
    <p style="font-size: 16px; font-weight: 600;">
        {{ _("Hello Learner") }},
    </p>
    <p>
        {{ _("A new course has been published on ")}} {{ brand_name }} {{ _("that might interest you!") }} {{ _("Here are the details:") }}
    </p>
    <div style="background-color: #F8F8F8; border-radius: 12px; padding: 12px; margin-bottom: 6px;">
        <div style="font-weight: 600; margin-bottom: 6px;">
            {{ title }}
        </div>
        <div>
            {{ short_introduction }}
        </div>
        <div style="margin-top: 20px;">
            {% for instructor in instructors %}
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    {% if instructor.user_image %}
                    <img src="{{ instructor.user_image }}" style="width: 20px; height: 20px; border-radius: 50%; margin-right: 5px;" />
                    {% else %}
                    <div style="width: 20px; height: 20px; border-radius: 50%; background-color: #ccc; display: flex; align-items: center; justify-content: center; margin-right: 5px;">
                        <span style="font-size: 12px; color: #fff;">
                            {{ instructor.full_name.split("")[0] | upper }}
                        </span>
                    </div>
                    {% endif %}
                    <div>
                        {{ instructor.full_name }}
                    </div>
                </div>
            {% endfor %}
        </div>
    </div>
    <a href="{{ course_url }}" style="display: inline-block; padding: 4px 8px; background-color: #171717; color: #fff; text-decoration: none; cursor: pointer; border-radius: 8px; margin-top: 10px;">
        {{ _("Checkout the course") }}
    </a>
</div>""",
	),
	"published_batch": (
		"Batch Published",
		'{{ _("A new course has been published on") }} {{ brand_name }}',
		"""<div style="width: 70%; margin: 0 auto;">
    <img src="{{ brand_logo }}" style="width: 30px; height: 30px;" />
    <p style="font-size: 16px; font-weight: 600;">
        {{ _("Hello Learner") }},
    </p>
    <p>
        {{ _("A new batch has been published on ")}} {{ brand_name }} {{ _("that might interest you!") }} {{ _("Here are the details:") }}
    </p>
    <div style="background-color: #F8F8F8; border-radius: 12px; padding: 12px; margin-bottom: 6px;">
        <div style="font-weight: 600; margin-bottom: 6px; font-size: 15px;">
            {{ title }}
        </div>
        <div>
            {{ short_introduction }}
        </div>
        <div style="margin-top: 20px; font-size: 13px;">
            {% if end_date %}
            <span>
                {{ _("From ") }} {{ frappe.utils.format_date(start_date, "dd MMM YYYY") }} {{ _(" to ") }} {{ frappe.utils.format_date(end_date, "dd MMM YYYY") }}
            </span>
            {% else %}
            <span>
                {{ frappe.utils.format_date(start_date, "dd MMM YYYY") }}
            </span>
            {% endif %}
        </div>
        <div style="color: #525252; margin-top: 4px; font-size: 13px;">
            <span>
                {{ _("Time: ") }} {{ frappe.utils.format_time(start_time, "HH:mm a") }} {{ timezone }}
            </span>
        </div>
        <div style="margin-top: 20px;">
            {% for instructor in instructors %}
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    {% if instructor.user_image %}
                    <img src="{{ instructor.user_image }}" style="width: 20px; height: 20px; border-radius: 50%; margin-right: 5px;" />
                    {% else %}
                    <div style="width: 20px; height: 20px; border-radius: 50%; background-color: #ccc; display: flex; align-items: center; justify-content: center; margin-right: 5px;">
                        <span style="font-size: 12px; color: #fff;">
                            {{ instructor.full_name.split("")[0] | upper }}
                        </span>
                    </div>
                    {% endif %}
                    <div>
                        {{ instructor.full_name }}
                    </div>
                </div>
            {% endfor %}
        </div>
    </div>
    <a href="{{ batch_url }}" style="display: inline-block; padding: 4px 8px; background-color: #171717; color: #fff; text-decoration: none; cursor: pointer; border-radius: 8px; margin-top: 10px;">
        {{ _("Checkout the batch") }}
    </a>
</div>""",
	),
	"course_interest": (
		"Interested User Alert",
		'{{ title }} {{ _("is available!") }}',
		"""<div>
	{% set site_link = "<a href='" + site_url + "'>" + app_name + "</a>" %}
	<p>{{ _("Hi {0},").format(first_name) }}</p>
  <br>
	<p>{{ _("The course {0} is now available on {1}.").format(frappe.bold(title), app_name) }}</p>
  <br>
	<p>Click on the link below to start learning.</p>
	<p style="margin: 15px 0px;">
		<a href="{{ course_link }}" rel="nofollow" class="btn btn-primary">{{ _("Start Learning") }}</a>
	</p>
	<br>
	<p>
		{{ _("You can also copy-paste following link in your browser") }}<br>
		<a href="{{ course_link }}">{{ site_url }}{{ course_link }}</a>
	</p>
	<br>
	<p>{{ _("Thanks and Regards") }},</p>
	<p>{{ app_name }}</p>
</div>""",
	),
	"batch_confirmation": (
		"Batch Enrollment Confirmation",
		'{{ _("Enrollment Confirmation for") }} {{ title }}',
		"""<p>
    {{ _("Dear ") }} {{ student_name }},
</p>
<br>
<p>
    {{ _("We are pleased to inform you that you have been enrolled in our upcoming batch. Congratulations!") }}
</p>
<br>

<p>
    <b>{{ _("Batch Start Date:") }}</b> {{ frappe.utils.format_date(start_date, "medium") }}
</p>

{% if medium %}
<p>
    <b>{{ _("Medium:") }}</b> {{ medium }}
</p>
{% endif %}

<p>
    <b>{{ _("Timings:") }}</b> {{ frappe.utils.format_time(start_time, "hh:mm a") }}
</p>
<br>
<p>
    {{ _("Visit the following link to view your ") }}
    <a href="{{ get_lms_route('batches/' ~ name) }}">{{ _("Batch Details") }}</a>
</p>
<p>
    {{ _("If you have any questions or require assistance, feel free to contact us.") }}
</p>
<br>
<p>
    {{ _("Best Regards") }}
</p>""",
	),
	"batch_start_reminder": (
		"Batch Starting Tomorrow",
		'{{ _("Your batch") }} {{ title }} {{ _("is starting tomorrow") }}',
		"""<p>
    {{ _("Dear ") }} {{ student_name }},
</p>
<br>
<p>
    {{ _("The batch you have enrolled for is starting tomorrow. Please be prepared and be on time for the session.") }}
</p>
<br>
<p>
    <b>{{ _("Batch:") }}</b> {{ title }}
</p>
<p>
    <b>{{ _("Start Date:") }}</b> {{ frappe.utils.format_date(start_date, "long") }}
</p>
<p>
    <b>{{ _("Timings:") }}</b> {{ frappe.utils.format_time(start_time, "hh:mm a") }}
</p>
<p>
    <b>{{ _("Medium:") }}</b> {{ medium }}
</p>
<br>
<p>
    <a href="{{ get_lms_route('batches/' ~ name) }}">👉 {{ _("Visit your batch") }}</a>
</p>
<br>
<p>
    {{ _("If you have any questions or require assistance, feel free to contact us.") }}
</p>
<br>
<p>
    {{ _("Best Regards") }}
</p>""",
	),
	"certification": (
		"Certificate Issued",
		'{{ _("Congratulations on getting certified!") }}',
		"""<p>
    {{ _("Dear ") }} {{ member_name }},
</p>
<br>
<p>
    {{ _("I am delighted to inform you that you have successfully earned your certification for the {0} course. Congratulations!").format(frappe.bold(course_title)) }}
</p>
<br>
<p>
    {{ _("With this certification, you can now showcase your updated skills and share your achievement with your colleagues and on LinkedIn. To access your certificate, please click on the link provided below. Make sure you are logged in to the portal.") }}
</p>
<br>
<a href="/api/method/frappe.utils.print_format.download_pdf?doctype=LMS+Certificate&name={{name}}&format={{template | urlencode }}">{{ _("Certificate Link") }}</a>
<br>
<p>
    {{ _("Once again, congratulations on this significant accomplishment.")}}
</p>
<br>
<p>
    {{ _("Best Regards") }}
</p>""",
	),
	"certificate_request_notification": (
		"Evaluation Slot Booked",
		'{{ _("Your evaluation slot has been booked") }}',
		"""<p> {{ _("Hey {0}").format(member_name) }} </p>
<br>
<p> {{ _('Your evaluation for the course {0} has been scheduled on {1} at {2} {3}.').format(course, date, start_time, timezone) }}</p>
<br>
<p> {{ _("Your evaluator is {0}").format(evaluator) }} </p>
<br>
<p> {{ _("Please prepare well and be on time for the evaluations.") }} </p>""",
	),
	"payment_reminder": (
		"Payment Reminder",
		'{{ _("Complete Your Enrollment - Don\'t miss out!") }}',
		"""<div>
    <p>{{ _('Hi') }} {{ billing_name }},</p>
    <br>
    <p>{{ _('We noticed that you started enrolling in the') }} {{ type }} {{ title }} {{ _('but didn’t complete your payment') }}.</p>
    <br>
    <p>
        {{ _("We have a limited number of seats, and they won't be available for long!")}}
    </p>
    <br>
    <p>
        {{ _("Don’t miss this opportunity to enhance your skills. Click below to complete your enrollment") }}:
    </p>
    <br>
    <p>
        <a href="{{ link }}">\U0001f449 {{ _("Complete Your Enrollment") }}</a>
    </p>
    <br>
    <p>
        {{ _("If you have any questions or need assistance, feel free to reach out to our support team.") }}
    </p>
    <br>
    <p>
        {{ _("Looking forward to seeing you enrolled!") }}
    </p>
</div>""",
	),
	"live_class_reminder": (
		"Live Class Today",
		'{{ _("Your class on") }} {{ title }} {{ _("is today") }}',
		"""<p>
    {{ _("Dear ") }} {{ student_name }},
</p>
<br>
<p>
    {{ _("You have a live class scheduled tomorrow. Please be prepared and be on time for the session.") }}
</p>
<br>
<p>
    <b>{{ _("Class:") }}</b> {{ title }}
</p>
<p>
    <b>{{ _("Date:") }}</b> {{ frappe.utils.format_date(date, "long") }}
</p>
<p>
    <b>{{ _("Timings:") }}</b> {{ frappe.utils.format_time(time, "hh:mm a") }}
</p>
<br>
<p>
    <a href="{{ get_lms_route('batches/' ~ batch_name) }}">\U0001f449 {{ _("Visit your batch") }}</a>
</p>
<br>
<p>
    {{ _("If you have any questions or require assistance, feel free to contact us.") }}
</p>
<br>
<p>
    {{ _("Best Regards") }}
</p>""",
	),
	"deadline_reminder_h3": (
		"Deadline in 3 Days",
		'{{ _("Deadline in") }} {{ days_left }} {{ _("days:") }} {{ item_title }}',
		"""<p>
    {{ _("Dear ") }} {{ student_name }},
</p>
<br>
<p>
    {% if days_left == 1 %}
    {{ _("This is a reminder that your deadline for {0} is tomorrow.").format(item_title) }}
    {% else %}
    {{ _("This is a reminder that your deadline for {0} is in {1} days.").format(item_title, days_left) }}
    {% endif %}
</p>
<br>
<p>
    <b>{{ _("Course:") }}</b> {{ course_title }}
</p>
<br>
<p>
    <a href="{{ course_url }}">\U0001f449 {{ _("Continue where you left off") }}</a>
</p>
<br>
<p>
    {{ _("If you have any questions or require assistance, feel free to contact us.") }}
</p>
<br>
<p>
    {{ _("Best Regards") }}
</p>""",
	),
	"deadline_reminder_h1": (
		"Deadline Tomorrow",
		'{{ _("Deadline tomorrow:") }} {{ item_title }}',
		"""<p>
    {{ _("Dear ") }} {{ student_name }},
</p>
<br>
<p>
    {% if days_left == 1 %}
    {{ _("This is a reminder that your deadline for {0} is tomorrow.").format(item_title) }}
    {% else %}
    {{ _("This is a reminder that your deadline for {0} is in {1} days.").format(item_title, days_left) }}
    {% endif %}
</p>
<br>
<p>
    <b>{{ _("Course:") }}</b> {{ course_title }}
</p>
<br>
<p>
    <a href="{{ course_url }}">\U0001f449 {{ _("Continue where you left off") }}</a>
</p>
<br>
<p>
    {{ _("If you have any questions or require assistance, feel free to contact us.") }}
</p>
<br>
<p>
    {{ _("Best Regards") }}
</p>""",
	),
	"mention_notification": (
		"Mentioned in a Comment",
		'{{ sender }} {{ _("mentioned you in a comment") }}',
		"""<p>
    {{ _("{0} mentioned you in a comment in your batch.").format(sender) }}
</p>
<p>
    <blockquote>
        {{ content | markdown }}
    </blockquote>
</p>
<div class="more-info">
	<a href="{{ link }}">{{ _("Check Discussion") }}</a>
</div>""",
	),
	"job_application": (
		"New Job Applicant",
		'{{ _("New Job Applicant") }}',
		"""<p>
    {{ _("{0} has applied for the job position {1}").format(full_name, job_title) }}
</p>
<br>
<p>
    {{ _("You can find their resume attached to this email.") }}
</p>""",
	),
	"job_report": (
		"Job Post Reported",
		'{{ _("User") }} {{ user }} {{ _("has reported the job post") }} {{ job }}',
		"""{% set job_link = "<a href='" + job_url + "'>" + job + "</a>" %}

<p>{{ _("Hey,") }}</p>
<p>{{ _("{0} has reported a job post for the following reason.").format(user) }}</p>
<p>" {{ reason }} "</p>
<p>{{ _("Please take appropriate action at {0}").format(job_url) }}</p>""",
	),
	"drip_unlock": (
		"New Content Unlocked",
		'{{ _("New content unlocked:") }} {{ item_title }}',
		"""<p>
    {{ _("Dear ") }} {{ student_name }},
</p>
<br>
<p>
    {{ _("New content just became available for you in {0}:").format(course_title) }}
</p>
<br>
<p>
    <b>{{ item_type }}:</b> {{ item_title }}
</p>
<br>
<p>
    <a href="{{ course_url }}">\U0001f449 {{ _("Continue where you left off") }}</a>
</p>
<br>
<p>
    {{ _("If you have any questions or require assistance, feel free to contact us.") }}
</p>
<br>
<p>
    {{ _("Best Regards") }}
</p>""",
	),
}


def execute():
	"""Copies each event's current file-based default wording into a real,
	editable Email Template - visible in Settings > Email > Templates - so an
	admin can see what an email currently says instead of it being invisible
	HTML only a developer can read. Deliberately does not touch
	LMS Email Notification.custom_template anywhere: nothing about what any
	email actually sends changes until an admin opens Settings > Email >
	Notifications and picks one of these themselves.
	"""
	for event_key, (label, subject, body) in _DEFAULT_TEMPLATES.items():
		if frappe.db.exists("Email Template", label):
			continue
		frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": label,
				"subject": subject,
				"response_html": body,
				"use_html": 1,
			}
		).insert(ignore_permissions=True)

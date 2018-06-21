PREREQ :=

# default to failsafe
DRYRUN := true
ifeq ($(DRYRUN),true)
	ECHO := echo
$(warning Not actually executing commands.  \
Pass DRYRUN=false to make to execute commands.)
else
	ECHO :=
endif

ifneq ($(filter iml_%,$(MAKECMDGOALS)),)
  COPR_CONFIG := --config include/copr-mfl
  OWNER_PROJECT = managerforlustre/manager-for-lustre-devel
else
  # local settings
  -include copr-local.mk

  ifeq ($(COPR_PROJECT),)
    PREREQ += create_copr_project
    COPR_PROJECT := $(NAME)
  endif
  ifneq ($(filter copr_%,$(MAKECMDGOALS)),)
    ifndef COPR_OWNER
      $(error COPR_OWNER needs to be set in copr-local.mk)
    endif
    ifndef COPR_PROJECT
      $(error COPR_PROJECT needs to be set in copr-local.mk)
    endif
  endif
  OWNER_PROJECT = $(COPR_OWNER)/$(COPR_PROJECT)
endif

ifeq ($(shell if grep -q ^%patch $(RPM_SPEC) ||   \
                 [ "$$(grep ^Source $(RPM_SPEC) | \
                       wc -l)" -gt 1 ]; then      \
                  echo SRPM;                      \
              else                                \
                  echo SPEC;                      \
             fi),SRPM)
  PREREQ += $(TARGET_SRPM)
else
  ifeq ($(UNPUBLISHED),true)
    PREREQ += $(TARGET_SRPM)
  else
    PREREQ += $(RPM_SPEC)
  endif
endif


delete_copr_project:
	if copr-cli list | grep $(NAME); then               \
	    $(ECHO) copr-cli $(COPR_CONFIG) delete $(NAME); \
	fi

create_copr_project: delete_copr_project
	$(ECHO) copr-cli $(COPR_CONFIG) create --chroot epel-7-x86_64 \
		 --enable-net on $(NAME)

ifeq ($(BUILD_METHOD),PyPI)
#copr_build:
# https://pagure.io/copr/copr/issue/207
copr_build iml_copr_build: $(PREREQ)
	# buildpypi is pretty useless right now:
	# https://pagure.io/copr/copr/issue/207
	#copr-cli buildpypi --packagename $(NAME)
	#$(COPR_OWNER)/$(COPR_PROJECT)
	$(ECHO) copr-cli $(COPR_CONFIG) build $(OWNER_PROJECT) $(filter-out \
		create_copr_project,$^)
else ifeq ($(BUILD_METHOD),SCM)
copr_build iml_copr_build: $(PREREQ)
	$(ECHO) copr-cli $(COPR_CONFIG) buildmock $(OWNER_PROJECT)       \
		 --scm-type git                                  \
		 --scm-url https://github.com/intel-hpdd/$(NAME)
else
copr_build iml_copr_build: $(PREREQ)
	$(ECHO) copr-cli $(COPR_CONFIG) build $(OWNER_PROJECT) $(filter-out \
		create_copr_project,$^)
endif

.PHONY: copr_build iml_copr_build
